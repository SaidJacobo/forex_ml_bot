from unittest.mock import patch

from backtesting import Backtest
import pandas as pd
import plotly.express as px
from backtesting._stats import compute_stats
import numpy as np


np.seterr(divide='ignore')

def plot_stats(data, stats, strategy, plot=False):
    equity_curve = stats._equity_curve
    aligned_data = data.reindex(equity_curve.index)
    bt = Backtest(aligned_data, strategy, cash=15_000, commission=0.002)
    print(stats)
    if plot:
        bt.plot(results=stats, resample=False)


def plot_full_equity_curve(df_equity, title):
 
    fig = px.line(x=df_equity.index, y=df_equity.Equity)
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Equity"
    )
    fig.update_traces(textposition="bottom right")
    fig.show()


def walk_forward(
        strategy,
        data_full,
        warmup_bars,
        lookback_bars=28*1440,
        validation_bars=7*1440,
        params=None,
        cash=15_000, 
        commission=0.0002,
        margin=1/30,
        verbose=False
):

    stats_master = []
    equity_final = None

    i = lookback_bars + warmup_bars  # El índice inicial es el final del primer lookback
    while i < len(data_full) - validation_bars:
        
        # Definimos los periodos de entrenamiento correctamente
        train_data = data_full.iloc[i - lookback_bars - warmup_bars: i]
        
        if verbose:
            print(f'train from {train_data.index[0]} to {train_data.index[-1]}')
        
        bt_training = Backtest(
            train_data, 
            strategy, 
            cash=cash, 
            commission=commission, 
            margin=margin
        )
        
        # Sobrescribir _tqdm usando patch para eliminar la barra de progreso
        with patch('backtesting.backtesting._tqdm', lambda *args, **kwargs: args[0]):
            stats_training = bt_training.optimize(
                **params
            )
        
        # El período de validación debe empezar justo al final del entrenamiento
        validation_data = data_full.iloc[i-warmup_bars: i+validation_bars]

        if verbose:
            print(f'validate from {validation_data.index[warmup_bars]} to {validation_data.index[-1]}')
        
        bt_validation = Backtest(
            validation_data, 
            strategy, 
            cash=cash if equity_final is None else equity_final, 
            commission=commission, 
            margin=margin
        )
        
        validation_params = {param: getattr(stats_training._strategy, param) for param in params.keys() if param != 'maximize'}
        
        if verbose:
            print(validation_params)
        
        stats_validation = bt_validation.run(
            **validation_params
        )
        
        equity_final = stats_validation['Equity Final [$]']
        if verbose:
            print(f'equity final: {equity_final}')
            print('=' * 32)

        stats_master.append(stats_validation)

        # Mover el índice `i` al final del período de validación actual
        i += validation_bars
    
    wfo_stats = get_wfo_stats(stats_master, warmup_bars, data_full)
    
    return wfo_stats


def get_wfo_stats(stats, warmup_bars, ohcl_data):
    trades = pd.DataFrame()
    for stat in stats:
        trades = pd.concat([trades, stat._trades])
    
    trades.EntryBar = trades.EntryBar.astype(int)
    trades.ExitBar = trades.ExitBar.astype(int)

    equity_curves = pd.DataFrame()
    for stat in stats:
        equity_curves = pd.concat([equity_curves, stat["_equity_curve"].iloc[warmup_bars:]])
        
    wfo_stats = compute_stats(
        trades=trades,  # broker.closed_trades,
        equity=equity_curves.Equity,
        ohlc_data=ohcl_data,
        risk_free_rate=0.0,
        strategy_instance=None  # strategy,
    )
    
    wfo_stats['_equity'] = equity_curves
    wfo_stats['_trades'] = trades
    
    return wfo_stats

def max_drawdown(serie):
    max_valor_acumulado = serie[0]
    max_dd = 0

    for valor_actual in serie[1:]:
        if valor_actual > max_valor_acumulado:
            max_valor_acumulado = valor_actual
        else:
            dd = (max_valor_acumulado - valor_actual) / max_valor_acumulado
            if dd > max_dd:
                max_dd = dd

    return max_dd

import numpy as np
import pandas as pd

def montecarlo_statistics_simulation(trade_history, n_simulations, initial_equity, threshold_ruin=0.85, return_raw_curves=False):
    # Parámetros iniciales
    n_steps = len(trade_history)
    mean_return = trade_history['ReturnPct'].mean()
    std_return = trade_history['ReturnPct'].std()

    drawdowns_pct = []  # Lista para almacenar los drawdowns en porcentaje
    final_returns_pct = []  # Lista para almacenar los retornos finales en porcentaje
    ruin_count = 0  # Contador de simulaciones que alcanzan la ruina
    ruin_threshold = initial_equity * threshold_ruin  # Umbral de ruina en términos de equidad

    # Función para calcular el drawdown máximo en porcentaje
    def max_drawdown(equity_curve):
        running_max = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - running_max) / running_max
        return np.min(drawdown) * 100  # Convertir el drawdown a porcentaje

    # Simulaciones de Montecarlo
    for _ in range(n_simulations):
        # Generar retornos aleatorios con media y desviación estándar de los históricos
        random_returns = np.random.normal(loc=mean_return, scale=std_return, size=n_steps)

        # Calcular la curva de equidad acumulada
        equity_curve = initial_equity * np.cumprod(1 + random_returns)

        # Calcular drawdown y almacenarlo en porcentaje
        dd_pct = max_drawdown(equity_curve)
        drawdowns_pct.append(dd_pct)

        # Calcular el retorno acumulado porcentual y almacenarlo
        final_return_pct = (equity_curve[-1] / initial_equity - 1) * 100  # Retorno final en porcentaje
        final_returns_pct.append(final_return_pct)

        # Verificar si la equidad cae por debajo del umbral de ruina en algún punto
        if np.any(equity_curve <= ruin_threshold):
            ruin_count += 1

    # Crear un DataFrame separado para los drawdowns y los retornos acumulados en porcentaje
    df_drawdowns = pd.DataFrame({'Drawdown (%)': drawdowns_pct})
    df_final_returns_pct = pd.DataFrame({'Final Return (%)': final_returns_pct})

    # Calcular las estadísticas usando df.describe() para cada DataFrame
    drawdown_stats = df_drawdowns.describe()
    return_stats = df_final_returns_pct.describe()

    # Calcular el riesgo de ruina
    risk_of_ruin = ruin_count / n_simulations

    # Agregar el riesgo de ruina a las estadísticas de drawdown
    drawdown_stats.loc['Risk of Ruin'] = risk_of_ruin

    # Combinar las métricas de drawdowns y retornos porcentuales
    combined_stats = pd.concat([drawdown_stats, return_stats], axis=1)
    if return_raw_curves:
        return combined_stats, df_drawdowns, df_final_returns_pct
        
    return combined_stats
