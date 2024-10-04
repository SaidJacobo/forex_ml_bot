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


def plot_full_equity_curve(df_equity):
 
    fig = px.line(x=df_equity.index, y=df_equity.Equity)
    fig.update_layout(
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

def montecarlo_simulation(trade_history, n_simulations, initial_equity, threshold_ruin):
    montecarlo_equity_curves = []

    ruin_count = 0  # Contador de simulaciones que alcanzan la ruina
    ruin_threshold = initial_equity * threshold_ruin  # Umbral de ruina en términos de equidad
    
    trade_history['Equity'] = initial_equity * (1 + trade_history['ReturnPct']).cumprod()


    for _ in range(0, n_simulations):
        shuffled_trades = trade_history['ReturnPct'].sample(frac=1).reset_index(drop=True)
        another_equity_curve = initial_equity * (1 + shuffled_trades).cumprod()
        montecarlo_equity_curves.append(another_equity_curve)   
        

    drawdowns = []

    for eq_curve in montecarlo_equity_curves:
        dd = max_drawdown(eq_curve)
        drawdowns.append(dd)
        
        if np.any(eq_curve <= ruin_threshold):
            ruin_count += 1
        

    print(f"Max Drawdown: {min(drawdowns):.2%}")
    print(f"Mean Drawdown: {np.mean(drawdowns):.2%}")
    print(f"median Drawdown: {np.median(drawdowns):.2%}")
    print(f"STD Drawdown: {np.std(drawdowns):.2%}")
    
    risk_of_ruin = ruin_count / n_simulations
    print(f"Risk of Ruin: {risk_of_ruin}")
    
    
def montecarlo_statistics_simulation(trade_history, n_simulations, initial_equity, threshold_ruin=0.95):
    # Parámetros iniciales
    n_steps = len(trade_history)

    mean_return = trade_history['ReturnPct'].mean()
    std_return = trade_history['ReturnPct'].std()

    drawdowns = []
    ruin_count = 0  # Contador de simulaciones que alcanzan la ruina
    ruin_threshold = initial_equity * threshold_ruin  # Umbral de ruina en términos de equidad

    # Función para calcular el drawdown máximo
    def max_drawdown(equity_curve):
        running_max = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - running_max) / running_max
        return np.min(drawdown)

    # Simulaciones de Montecarlo
    for _ in range(n_simulations):
        # Generar retornos aleatorios con media y desviación estándar de los históricos
        random_returns = np.random.normal(loc=mean_return, scale=std_return, size=n_steps)

        # Calcular la curva de equidad acumulada
        equity_curve = initial_equity * np.cumprod(1 + random_returns)

        # Calcular drawdown
        dd = max_drawdown(equity_curve)
        drawdowns.append(dd)

        # Verificar si la equidad cae por debajo del umbral de ruina en algún punto
        if np.any(equity_curve <= ruin_threshold):
            ruin_count += 1

    # Calcular estadísticas de drawdowns
    print(f"Max Drawdown: {min(drawdowns):.2%}")
    print(f"Mean Drawdown: {np.mean(drawdowns):.2%}")
    print(f"Median Drawdown: {np.median(drawdowns):.2%}")
    print(f"STD Drawdown: {np.std(drawdowns):.2%}")

    # Calcular y mostrar el Risk of Ruin
    risk_of_ruin = ruin_count / n_simulations
    print(f"Risk of Ruin: {risk_of_ruin:.2%}")
