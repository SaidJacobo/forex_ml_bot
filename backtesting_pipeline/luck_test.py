import os
import sys

current_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
    
import re
import uuid
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
import yaml
import plotly.graph_objects as go
from backbone.utils.montecarlo_utils import max_drawdown

pd.set_option('display.max_columns', 500) # number of columns to be displayed


def find_matching_files(directory, ticker, interval):
    pattern = rf"^{ticker}_{interval}_.+_.+\.csv$"
    all_files = os.listdir(directory)
    matching_files = [file for file in all_files if re.match(pattern, file)]

    return matching_files

def replace_in_document(obj, element_to_replace, element):
    if isinstance(obj, dict):
        return {k: replace_in_document(v, element_to_replace, element) for k, v in obj.items()}
    elif isinstance(obj, str):
        return obj.replace(element_to_replace, element)
    return obj

if __name__ == '__main__':
    with open("./backtesting_pipeline/configs/backtest_params.yml", "r") as file_name:
        bt_params = yaml.safe_load(file_name)
    
    config_path = bt_params['config_path']
    initial_cash = bt_params["initial_cash"]
    risk = bt_params["risk"]
    
    with open(config_path, "r") as file_name:
        configs = yaml.safe_load(file_name)

    strategy_name = bt_params["strategy_name"]
    configs = replace_in_document(obj=configs, element_to_replace="{strategy_name}", element=strategy_name)
    configs = replace_in_document(obj=configs, element_to_replace="{risk}", element=str(risk))
          
    configs = configs["luck_test"]

    in_path = configs['in_path']
    root_path = configs['root_path']
    trades_percent_to_remove = configs['trades_percent_to_remove']
    out_path = configs['out_path']
    run_only_in = configs['run_only_in']
    
    if not os.path.exists(out_path):
        os.makedirs(out_path)
        
    filter_performance = pd.read_csv(os.path.join(in_path, "filter_performance.csv"))
    
    if run_only_in:
        filter_performance['ticker_interval'] = filter_performance['ticker'] + '_' + filter_performance['interval'].astype(str)
        filter_performance = filter_performance[filter_performance['ticker_interval'].isin(run_only_in)]

    all_opt_params = {}
    symbols = {}
    stats_per_symbol = {}
    all_metrics = pd.DataFrame()

    for _, row in filter_performance.iterrows():
        ticker = row.ticker
        interval = row.interval
        method = row.method
        strategy = row.strategy
        
        # busco los trades para obtener sus probs
        trades = pd.read_csv(
            os.path.join(root_path, method, f'{ticker}_{interval}', 'trades.csv')
        )

        trades['id'] = [uuid.uuid4() for _ in range(len(trades.index))]

        trades_to_remove = round((trades_percent_to_remove/100) * trades.shape[0])
        
        top_best_trades = trades.sort_values(by='ReturnPct', ascending=False).head(trades_to_remove)
        top_worst_trades = trades.sort_values(by='ReturnPct', ascending=False).tail(trades_to_remove)
        
        trades_to_remove *= 2
        
        filtered_trades = trades[
            (~trades['id'].isin(top_best_trades.id))
            & (~trades['id'].isin(top_worst_trades.id))
            & (~trades['ReturnPct'].isna())
        ].sort_values(by='ExitTime')

        filtered_trades['Equity'] = 0
        filtered_trades['Equity'] = initial_cash * (1 + filtered_trades.ReturnPct).cumprod()
        
        dd = -1 * max_drawdown(filtered_trades['Equity'])
        ret = ((filtered_trades.iloc[-1]['Equity'] - filtered_trades.iloc[0]['Equity']) / filtered_trades.iloc[0]['Equity']) * 100
        ret_dd = ret / dd
        custom_metric = (ret / (1 + dd)) * np.log(1 + filtered_trades.shape[0])  
        
        x = np.arange(filtered_trades.shape[0]).reshape(-1, 1)
        reg = LinearRegression().fit(x, filtered_trades['Equity'])
        stability_ratio = reg.score(x, filtered_trades['Equity'])
        
        metrics = pd.DataFrame({
            'strategy': [f'take_off_{trades_to_remove}_trades'],
            'ticker': [ticker],
            'interval': [interval],
            'stability_ratio': [stability_ratio],
            'return': [ret],
            'drawdown': [dd],
            'return_drawdown': [ret_dd],
            'custom_metric': [custom_metric],
        })
    
        all_metrics = pd.concat([all_metrics, metrics])

        # Create traces
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trades.ExitTime, y=trades.Equity,
                            mode='lines',
                            name='equity original'))

        fig.add_trace(go.Scatter(x=filtered_trades.ExitTime, y=filtered_trades.Equity,
                            mode='lines',
                            name=f'take_of_{trades_to_remove}_trades'))

        fig.update_layout(
            title=f"{strategy_name}_{ticker}_{interval}",
            xaxis_title='Time',
            yaxis_title='Equity'
        )

        fig.show()
        
        fig.write_html(
            os.path.join(out_path, f'{strategy_name}_{ticker}_{interval}.html')
        )

    all_metrics.to_csv(
        os.path.join(out_path, 'luck_test_performance.csv'), index=False
    )
    
    
    
    