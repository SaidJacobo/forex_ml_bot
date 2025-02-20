from typing import List
import numpy as np
from pandas import DataFrame
from sklearn.linear_model import LinearRegression
from app.backbone.entities.bot_performance import BotPerformance
from app.backbone.entities.trade import Trade
import pandas as pd

def _performance_from_df_to_obj(
    df_performance: DataFrame, 
    date_from, 
    date_to, 
    risk, 
    method, 
    bot, 
    initial_cash, 
    metatrader_name
    ):
    performance_for_db = [BotPerformance(**row) for _, row in df_performance.iterrows()].pop()
    performance_for_db.DateFrom = date_from
    performance_for_db.DateTo = date_to
    performance_for_db.Risk = risk
    performance_for_db.Method = method
    performance_for_db.Bot = bot
    performance_for_db.InitialCash = initial_cash
    performance_for_db.MetaTraderName = metatrader_name
    
    return performance_for_db

def get_trade_df_from_db(trades: List[Trade], performance_id):
    data = [{
            'Id': trade.Id,
            'BotPerformanceId': performance_id,
            'Size': trade.Size,
            'EntryBar': trade.EntryBar,
            'ExitBar': trade.ExitBar,
            'EntryPrice': trade.EntryPrice,
            'ExitPrice': trade.ExitPrice,
            'PnL': trade.PnL,
            'ReturnPct': trade.ReturnPct,
            'EntryTime': trade.EntryTime,
            'ExitTime': trade.ExitTime,
            'Duration': trade.Duration,
            'Equity': trade.Equity,
            'TopBest': trade.TopBest,
            'TopWorst': trade.TopWorst,
        }
        for trade in trades
    ]
    
    trade_history = pd.DataFrame(data)
    trade_history['ExitTime'] = pd.to_datetime(trade_history['ExitTime'])
    trade_history = trade_history.sort_values(by='ExitTime')
    trade_history.set_index('ExitTime', inplace=True)
    
    return trade_history

def get_date_range(equity_curves: pd.DataFrame):
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

    date_range = pd.to_datetime(pd.date_range(start=min_date, end=max_date, freq='D'))
    return date_range

def get_portfolio_equity_curve(equity_curves: pd.DataFrame, initial_equity: float) -> pd.Series:
    
    date_range = get_date_range(equity_curves=equity_curves)
    
    total = pd.DataFrame()

    for name, curve in equity_curves.items():
        eq = curve.copy()
        eq = eq.reset_index().sort_values(by='ExitTime')
        eq['ExitTime'] = eq['ExitTime'].dt.floor('D').dt.date

        eq = eq.groupby('ExitTime').agg({'Equity':'last'})

        eq = eq.reindex(date_range)
        
        eq.Equity = eq.Equity.ffill()
        eq.Equity = eq.Equity.fillna(initial_equity)
    
        eq['variacion'] = eq['Equity'] - eq['Equity'].shift(1)
        eq['variacion_porcentual'] = eq['variacion'] / eq['Equity'].shift(1)
        
        df_variacion = pd.DataFrame(
            {
                f'variacion_{name}': eq.variacion_porcentual.fillna(0)
            }
        )
        
        total = pd.concat([total, df_variacion], axis=1)

    total = total.reset_index().rename(columns={'index':'ExitTime'})

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

    total = total.set_index('ExitTime')
    
    return total[['Equity']]

def calculate_stability_ratio(equity_curve: pd.Series):
    x = np.arange(len(equity_curve)).reshape(-1, 1)
    reg = LinearRegression().fit(x, equity_curve)
    stability_ratio = reg.score(x, equity_curve)
    
    return stability_ratio

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