
import yaml
import MetaTrader5 as mt5
import pandas as pd
import os
import numpy as np
import re
import pandas as pd
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import plotly.express as px
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

pd.set_option('display.max_columns', 500) # number of columns to be displayed

def max_drawdown(equity_curve, verbose=True):
    # Calcular el running max de la equity curve
    running_max = np.maximum.accumulate(equity_curve)
    
    # Calcular el drawdown
    drawdown = (equity_curve - running_max) / running_max
    
    # Encontrar el valor máximo de drawdown y la fecha correspondiente
    max_drawdown_value = np.min(drawdown) * 100  # Convertir el drawdown a porcentaje
    max_drawdown_date = equity_curve.index[np.argmin(drawdown)]
    
    if verbose:
        print(f"Máximo drawdown: {max_drawdown_value:.2f}%")
        print(f"Fecha del máximo drawdown: {max_drawdown_date}")

    return max_drawdown_value

def get_hipotetical_wallet_equity(equity_curves, initial_equity):
    total = pd.DataFrame()

    for name, curve in equity_curves.items():
        eq = curve.copy()
        eq = eq.reset_index().rename(columns={'index':'Date'})[['Date','Equity']].sort_values(by='Date')
        eq['Date'] = pd.to_datetime(eq['Date'])
        eq['Date'] = eq['Date'].dt.floor('D').dt.date

        eq = eq.groupby('Date').agg({'Equity':'last'})

        eq = eq.reindex(date_range)
        
        eq.Equity = eq.Equity.ffill()
        eq.Equity = eq.Equity.fillna(INITIAL_CASH)
    
        eq['variacion'] = eq['Equity'] - eq['Equity'].shift(1)
        eq['variacion_porcentual'] = eq['variacion'] / eq['Equity'].shift(1)
        
        df_variacion = pd.DataFrame(
            {
                f'variacion_{name}': eq.variacion_porcentual.fillna(0)
            }
        )
        
        total = pd.concat([total, df_variacion], axis=1)

    total = total.reset_index().rename(columns={'index':'Date'})

    # Inicializa el valor de equity
    total['Equity'] = initial_equity

    # Lista de columnas con las variaciones porcentuales
    variation_cols = [col for col in total.columns if col.startswith('variacion')]

    # Calcular la curva de equity
    for i in range(1, len(total)):
        previous_equity = total.loc[i-1, 'Equity']  # Equity del periodo anterior
        
        # Calcula el impacto monetario de cada bot por separado y suma el resultado
        impact_sum = 0
        for col in variation_cols:
            variation = total.loc[i, col]
            impact_sum += previous_equity * variation
        
        # Actualiza el equity sumando el impacto monetario total
        total.loc[i, 'Equity'] = previous_equity + impact_sum

    # Resultado final

    total = total.set_index('Date')
    return total[['Equity']]

def calculate_margin_metrics(all_trades, portfolio_equity_curve):
    # Convertir columnas a datetime
    for df in all_trades.values():
        df["EntryTime"] = pd.to_datetime(df["EntryTime"])
        df["ExitTime"] = pd.to_datetime(df["ExitTime"])

    # Concatenar y calcular los eventos
    all_events = pd.concat([
        pd.concat([
            df[["EntryTime", "margin"]].rename(columns={"EntryTime": "time", "margin": "change"}).round(3),
            df[["ExitTime", "margin"]].rename(columns={"ExitTime": "time", "margin": "change"}).assign(change=lambda x: -x["change"]).round(3)
        ]) for df in all_trades.values()
    ])

    # Ordenar por tiempo
    all_events = all_events.sort_values(['time', 'change'], ascending=[True, False]).reset_index(drop=True)

    # Calcular el margen acumulado
    all_events["margin"] = all_events["change"].cumsum()


    all_events['time'] = pd.to_datetime(all_events['time']).dt.date
    all_events.set_index('time', inplace=True)

    all_events = pd.merge(
        all_events,
        portfolio_equity_curve,
        left_index=True,
        right_index=True,
        how='left'
    )

    all_events = all_events.round(2)

    all_events['margin_level'] = ((all_events['Equity'] / all_events['margin']) * 100)

    all_events['free_margin'] = (all_events['Equity'] - all_events['margin'])

    stop_outs = all_events[(all_events['margin_level'] < 50) & (all_events['margin_level'] != -1*np.inf)]
    margin_calls = all_events[(all_events['margin_level'] < 100) & (all_events['margin_level'] != -1*np.inf)]
    
    return all_events, margin_calls, stop_outs

def ftmo_simulator(equity_curve, initial_cash):
    equity_curve['month'] = pd.to_datetime(equity_curve.index)
    equity_curve['month'] = pd.to_datetime(equity_curve['month'], errors='coerce')  # Asegúrate de que sea datetime
    equity_curve['month'] = equity_curve['month'].dt.to_period('M')  # Convertir a un periodo mensual
    
    equity_curve.fillna(0, inplace=True)

    # Identificar índices de los valores máximo y mínimo por mes
    max_indices = equity_curve.groupby('month')['Equity'].idxmax()
    min_indices = equity_curve.groupby('month')['Equity'].idxmin()

    # Combinar índices únicos
    unique_indices = pd.Index(max_indices).union(pd.Index(min_indices))

    equity_curve = equity_curve.loc[unique_indices]
    
    # Inicializar acumuladores globales
    total_positive_hits = 0
    total_negative_hits = 0
    all_time_to_positive = []
    all_time_to_negative = []

    # Simulación para cada mes como punto de partida
    for i in range(0, len(equity_curve), 2):
        perc_change = 0
        time_to_positive = []
        time_to_negative = []
        
        actual_equity = equity_curve.iloc[i].Equity
        
        months_elapsed = 0

        # Iterar desde el mes de inicio hacia adelante
        for j in range(i, len(equity_curve)):
            
            future_equity = equity_curve.iloc[j].Equity
            
            if i == 0 and j == 0:
                perc_change = ((future_equity - initial_cash) / initial_cash) * 100
                
            else:
                perc_change = ((future_equity - actual_equity) / actual_equity) * 100
            
            months_elapsed += 0.5

            if perc_change >= 10:
                total_positive_hits += 1
                time_to_positive.append(months_elapsed)
                months_elapsed = 0
                break

            elif perc_change <= -10:
                total_negative_hits += 1
                time_to_negative.append(months_elapsed)
                months_elapsed = 0
                break

        # Guardar tiempos de esta simulación
        all_time_to_positive.extend(time_to_positive)
        all_time_to_negative.extend(time_to_negative)

    return total_positive_hits, total_negative_hits, all_time_to_positive, all_time_to_negative

def get_percentual_differences(equity_curves):
    percentual_differences = {}
    
    for name, curve in equity_curves.items():
        equity_df = curve.copy()
        
        equity_df = equity_df.reset_index().rename(columns={'index':'Date'})
        equity_df['Date'] = pd.to_datetime(equity_df['Date'])
        equity_df['Date'] = equity_df['Date'].dt.floor('D').dt.date
        
        equity_df = pd.DataFrame(equity_df.groupby('Date')['Equity'].last()).reindex(date_range)
        equity_df.ffill(inplace=True)
        equity_df.fillna(INITIAL_CASH, inplace=True)

        equity_df['diff'] = equity_df['Equity'] - equity_df['Equity'].shift(1)
        
        percentual_differences[name] = equity_df
    
    return percentual_differences

timeframes_to_number = {
    'H1': 16385,
    'H2': 16386,
    'H3': 16387,
    'H4': 16388,
}

if __name__ == '__main__':
    INITIAL_CASH = 10_000

    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
        quit()

    root = './backbone/data'

    with open("./configs/leverages.yml", "r") as file_name:
        leverages = yaml.safe_load(file_name)

    equity_curves = {}
    all_trades = {}
    root = './backtesting_pipeline/portfolio_4'

    strategies = [stgy for stgy in os.listdir(root) if not stgy.endswith('.txt')]

    print(strategies)

    for strategy in strategies:
        
        tickers_timeframes = os.listdir(os.path.join(root, strategy, 'preliminar_analysis'))
        tickers_timeframes = [file for file in tickers_timeframes if not re.match(r".*\.\w+$", file)]
        tickers_timeframes = [file for file in tickers_timeframes if '_' in file]
        
        print(tickers_timeframes)
        
        for ticker_timeframe in tickers_timeframes:
            
            ticker = ticker_timeframe.split('_')[0]
            leverage = leverages[ticker]
            
            
            equity = pd.read_csv(
                os.path.join(root, strategy, 'preliminar_analysis', ticker_timeframe, 'equity.csv'), index_col=0
            )
            equity.index = pd.to_datetime(equity.index)
            equity_curves[ticker_timeframe] = equity
            
            trades = pd.read_csv(
                os.path.join(root, strategy, 'preliminar_analysis', ticker_timeframe, 'trades.csv')
            )
            
            trades['margin'] = (np.abs(trades['Size']) * trades['EntryPrice']) / leverage
            
            all_trades[ticker_timeframe] = trades

    min_date = None
    max_date = None

    for name, curve in equity_curves.items():
        # Convertir las fechas a UTC si son tz-naive
        actual_date = curve.index[0].tz_localize('UTC') if curve.index[0].tz is None else curve.index[0].tz_convert('UTC')
        
        # Si min_date es None, inicializar con la primera fecha
        if min_date is None:
            min_date = actual_date
        # Comparar si la fecha actual es menor que min_date
        elif actual_date < min_date:
            min_date = actual_date

        # Si max_date es None, inicializar con la última fecha
        curve_last_date = curve.index[-1].tz_localize('UTC') if curve.index[-1].tz is None else curve.index[-1].tz_convert('UTC')
        
        if max_date is None:
            max_date = curve_last_date
        # Comparar si la fecha actual es mayor que max_date
        elif curve_last_date > max_date:
            max_date = curve_last_date

    # Mostrar las fechas encontradas
    print(f"Min Date: {min_date}")
    print(f"Max Date: {max_date}")

    # Calcular min_date y max_date
    min_date = min_date.date()
    max_date = max_date.date()

    print(min_date)
    print(max_date)

    date_range = pd.to_datetime(pd.date_range(start=min_date, end=max_date, freq='D'))
    print(date_range)
                
    equity_portfolio = get_hipotetical_wallet_equity(equity_curves=equity_curves, initial_equity=INITIAL_CASH)
    equity_curves['variaciones_porcentuales'] = equity_portfolio

    # Crear una figura vacía
    fig = go.Figure()

    # Recorrer las curvas de equity de cada bot y agregarlas al gráfico
    for k, v in equity_curves.items():
        fig.add_trace(go.Scatter(x=v.index, y=v.Equity, mode='lines', name=k))

    # Actualizar los detalles del layout del gráfico
    fig.update_layout(
        title="Curvas de Equity de Múltiples Bots",
        xaxis_title="Fecha",
        yaxis_title="Equity",
        legend_title="Bots"
    )

    # Mostrar el gráfico
    fig.show()

    max_drawdown(equity_curves['variaciones_porcentuales'])

    df = equity_curves["variaciones_porcentuales"]
    df.index = pd.to_datetime(df.index)

    # Calcular los retornos diarios en porcentaje
    df['Daily Return'] = ((df['Equity'] - df['Equity'].shift(1)) / df['Equity'].shift(1)) * 100

    # Crear un DataFrame resampleado con valores mínimo y máximo para cada mes
    monthly_min = df['Daily Return'].resample("M").min()
    monthly_max = df['Daily Return'].resample("M").max()

    # Aplicar la lógica de np.where para seleccionar el mínimo si < 0, máximo si >= 0
    monthly_returns = np.where(monthly_max >= 0, monthly_max, monthly_min)

    # Crear un índice temporal basado en las fechas de los datos mensuales
    monthly_index = df['Daily Return'].resample("M").apply(lambda x: x.index[-1])

    # Crear un DataFrame para el gráfico
    monthly_df = pd.DataFrame({
        'Fecha': monthly_index,
        'Retorno Mensual': monthly_returns
    })

    print(monthly_df['Retorno Mensual'].mean())
        
    positive_hits, negative_hits, time_to_positive, time_to_negative = ftmo_simulator(equity_curves['variaciones_porcentuales'], 10_000)

    print('positive_hits: ', positive_hits)
    print('negative_hits: ', negative_hits)
    print('mean_time_to_positive: ', np.mean(time_to_positive))
    print('std_time_to_positive: ', np.std(time_to_positive))
    
    all_events, margin_calls, stop_outs = calculate_margin_metrics(all_trades, equity_curves['variaciones_porcentuales'])
    
    
    del equity_curves['variaciones_porcentuales']
    
    differences = get_percentual_differences(equity_curves)
    differences
    
    # Paso 1: Unir todas las curvas de equity en un solo DataFrame basado en la fecha
    all_equity_df = pd.DataFrame()

    for name, df in differences.items():
        all_equity_df[name] = df.resample('M').agg({'Equity':'last','diff':'sum',})['diff']

    correlation_matrix = all_equity_df.corr(method='pearson')

    plt.figure(figsize=(12, 8))
    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', vmin=-1, vmax=1)
    plt.title('Correlation Matrix of Equity Curves')
    plt.xticks(rotation=75)
    plt.show()
    