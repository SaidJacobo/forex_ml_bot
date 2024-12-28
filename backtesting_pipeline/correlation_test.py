import os
import sys

current_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
    
import re
import pandas as pd
import yaml
import plotly.express as px
import numpy as np
from sklearn.linear_model import LinearRegression


def find_matching_files(directory, ticker, interval):
    pattern = rf"^{ticker}_{interval}_.+_.+\.csv$"
    all_files = os.listdir(directory)
    matching_files = [file for file in all_files if re.match(pattern, file)]

    return matching_files

def replace_strategy_name(obj, name):
    if isinstance(obj, dict):
        return {k: replace_strategy_name(v, name) for k, v in obj.items()}
    elif isinstance(obj, str):
        return obj.replace("{strategy_name}", name)
    return obj

if __name__ == '__main__':
    with open("./backtesting_pipeline/configs/backtest_params.yml", "r") as file_name:
        bt_params = yaml.safe_load(file_name)
    
    config_path = bt_params['config_path']
    
    with open(config_path, "r") as file_name:
        configs = yaml.safe_load(file_name)

    strategy_name = bt_params["strategy_name"]
    configs = replace_strategy_name(obj=configs, name=strategy_name)
          
    configs = configs["correlation_test"]

    in_path = configs['in_path']
    data_path = configs['data_path']
    root_path = configs['root_path']
    out_path = configs['out_path']
    show = configs['show']
    run_only_in = configs['run_only_in']
    
    if not os.path.exists(out_path):
        os.makedirs(out_path)
        
    filter_performance = pd.read_csv(os.path.join(in_path, "filter_performance.csv"))
    
    if run_only_in:
        filter_performance['ticker_interval'] = filter_performance['ticker'] + '_' + filter_performance['interval'].astype(str)
        filter_performance = filter_performance[filter_performance['ticker_interval'].isin(run_only_in)]

    result = pd.DataFrame()

    for _, row in filter_performance.iterrows():
        ticker = row.ticker
        interval = row.interval
        method = row.method
        strategy = row.strategy
        
        path = os.path.join(data_path, "data")
        matching_file = find_matching_files(path, ticker, interval).pop()

        # busco el df del activo
        prices = pd.read_csv(os.path.join(path, matching_file))
        prices["Date"] = pd.to_datetime(prices["Date"])
        
        equity = pd.read_csv(
            os.path.join(root_path, method, f'{ticker}_{interval}', 'equity.csv'), index_col=0
        )
        
        # Transformar el índice al formato mensual
        equity = equity.reset_index().rename(columns={'index': 'Date'})
        equity['month'] = pd.to_datetime(equity['Date']).dt.to_period('M')
        equity = equity.groupby(by='month').agg({'Equity': 'last'})
        equity['perc_diff'] = (equity['Equity'] - equity['Equity'].shift(1)) / equity['Equity'].shift(1)
        equity.fillna(0, inplace=True)

        # Crear un rango completo de meses con PeriodIndex
        full_index = pd.period_range(start=equity.index.min(), end=equity.index.max(), freq='M')

        # Reindexar usando el rango completo de PeriodIndex
        equity = equity.reindex(full_index)
        equity = equity.fillna(method='ffill')
        
        prices['month'] = pd.to_datetime(prices['Date'])
        prices['month'] = prices['month'].dt.to_period('M')
        prices = prices.groupby(by='month').agg({'Close':'last'})
        prices['perc_diff'] = (prices['Close'] - prices['Close'].shift(1)) / prices['Close'].shift(1)
        prices.fillna(0, inplace=True)
        
        prices = prices[prices.index.isin(equity.index)]
        
        # Datos
        x = np.array(prices['perc_diff']).reshape(-1, 1)
        y = equity['perc_diff']
        
        # Ajustar el modelo de regresión lineal
        reg = LinearRegression().fit(x, y)
        determination = reg.score(x, y)
        correlation = np.corrcoef(prices['perc_diff'], equity['perc_diff'])[0, 1]

        # Predicciones para la recta
        x_range = np.linspace(x.min(), x.max(), 100).reshape(-1, 1)  # Rango de X para la recta
        y_pred = reg.predict(x_range)  # Valores predichos de Y

        # Crear el gráfico
        fig = px.scatter(
            x=prices['perc_diff'], y=equity['perc_diff'],
        )

        # Agregar la recta de regresión
        fig.add_scatter(x=x_range.flatten(), y=y_pred, mode='lines', name='Regresión Lineal')

        # Personalización
        fig.update_layout(
            title=f"Correlación {strategy_name} con {ticker}_{interval}",
            xaxis_title=f'{ticker}_{interval} Monthly Price Variation',
            yaxis_title=f'{strategy_name} Monthly Returns'
        )

        # Agregar anotación con los valores R² y Pearson
        fig.add_annotation(
            x=0.95,  # Posición en el gráfico (en unidades de fracción del eje)
            y=0.95,
            xref='paper', yref='paper',
            text=f"<b>r = {correlation:.3f}<br>R² = {determination:.3f}</b>",
            showarrow=False,
            font=dict(size=16, color="black"),
            align="left",
            bordercolor="black",
            borderwidth=1,
            borderpad=4,
            bgcolor="white",
            opacity=0.8
        )

        if show:
            fig.show()
        
        fig.write_html(
            os.path.join(out_path, f'{strategy_name}_{ticker}_{interval}.html')
        )
        
    
        
        result = pd.concat([
            result,
            pd.DataFrame({
                'strategy': [f'{strategy_name}_{ticker}_{interval}'],
                'correlation': [correlation],
                'determination': [determination],
            })
        ])
    
    result = result.round(3)
    
    result.to_csv(
        os.path.join(out_path, 'correlation_results.csv'),
        index=False
    )