from backbone.utils.general_purpose import transformar_a_uno
from unittest.mock import patch
from backtesting import Backtest
import pandas as pd
import plotly.express as px
from backtesting._stats import compute_stats
import numpy as np
import itertools
from sklearn.linear_model import LinearRegression
import MetaTrader5 as mt5
import numpy as np
from sklearn.linear_model import LinearRegression


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

    # Iniciar el índice en el final del primer lookback
    i = lookback_bars + warmup_bars  

    while i < len(data_full):

        # Definir el periodo de entrenamiento correctamente
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
        
        # Sobrescribir _tqdm para eliminar la barra de progreso
        with patch('backtesting.backtesting._tqdm', lambda *args, **kwargs: args[0]):
            stats_training = bt_training.optimize(
                **params
            )
        
        # Ajustar el tamaño del periodo de validación al final del dataset
        remaining_bars = len(data_full) - i
        current_validation_bars = min(validation_bars, remaining_bars)

        # El período de validación empieza justo al final del entrenamiento
        validation_data = data_full.iloc[i - warmup_bars: i + current_validation_bars]

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
        i += current_validation_bars
    
    wfo_stats = get_wfo_stats(stats_master, warmup_bars, data_full)
    
    return wfo_stats


def get_wfo_stats(stats, warmup_bars, ohcl_data):
    trades = pd.DataFrame(columns=['Size','EntryBar','ExitBar','EntryPrice','ExitPrice','PnL','ReturnPct','EntryTime','ExitTime', 'Duration'])
    for stat in stats:
        trades = pd.concat([trades, stat._trades])
    
    trades.EntryBar = trades.EntryBar.astype(int)
    trades.ExitBar = trades.ExitBar.astype(int)

    equity_curves = pd.DataFrame(columns=['Equity',  'DrawdownPct', 'DrawdownDuration'])
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

def montecarlo_statistics_simulation(
        trade_history, 
        equity_curve, 
        n_simulations, 
        initial_equity, 
        threshold_ruin=0.85, 
        return_raw_curves=False,
        percentiles=None
    ):
        
    # Renombro las columnas
    trade_history = trade_history.rename(columns={'ExitTime':'Date'})
    trade_history = trade_history[['Date', 'PnL']]
    
    equity_curve = equity_curve.reset_index().rename(columns={'index':'Date'})[['Date','Equity']].sort_values(by='Date')

    trade_history['Date'] = pd.to_datetime(trade_history['Date'])
    equity_curve['Date'] = pd.to_datetime(equity_curve['Date'])

    # joineo los dfs por fechas
    full_df = pd.merge(
        equity_curve,
        trade_history,
        on='Date',
        how='left'   
    )

    full_df = full_df[~full_df['PnL'].isna()]
    
    # Porcentaje de ganancia
    full_df['pct'] = full_df['PnL'] / full_df['Equity'].shift(1)

    # Parámetros iniciales
    n_steps = len(trade_history)
    mean_return = full_df['pct'].mean()
    std_return = full_df['pct'].std()

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
        synthetic_equity_curve = initial_equity * np.cumprod(1 + random_returns)

        # Calcular drawdown y almacenarlo en porcentaje
        dd_pct = max_drawdown(synthetic_equity_curve)
        drawdowns_pct.append(dd_pct)

        # Calcular el retorno acumulado porcentual y almacenarlo
        final_return_pct = (synthetic_equity_curve[-1] / initial_equity - 1) * 100  # Retorno final en porcentaje
        final_returns_pct.append(final_return_pct)

        # Verificar si la equidad cae por debajo del umbral de ruina en algún punto
        if np.any(synthetic_equity_curve <= ruin_threshold):
            ruin_count += 1

    # Crear un DataFrame separado para los drawdowns y los retornos acumulados en porcentaje
    df_drawdowns = pd.DataFrame({'Drawdown (%)': drawdowns_pct})
    df_final_returns_pct = pd.DataFrame({'Final Return (%)': final_returns_pct})

    # Calcular las estadísticas usando df.describe() para cada DataFrame
    if not percentiles:
        drawdown_stats = df_drawdowns.describe()
        return_stats = df_final_returns_pct.describe()
    else:
        drawdown_stats = df_drawdowns.describe(percentiles=percentiles)
        return_stats = df_final_returns_pct.describe(percentiles=percentiles)
        

    # Calcular el riesgo de ruina
    risk_of_ruin = ruin_count / n_simulations

    # Agregar el riesgo de ruina a las estadísticas de drawdown
    drawdown_stats.loc['Risk of Ruin'] = risk_of_ruin

    # Combinar las métricas de drawdowns y retornos porcentuales
    combined_stats = pd.concat([drawdown_stats, return_stats], axis=1)
    if return_raw_curves:
        return combined_stats, df_drawdowns, df_final_returns_pct
        
    return combined_stats


def run_wfo(
        strategy,
        ticker,
        interval, 
        prices: pd.DataFrame, 
        initial_cash:float,
        commission:float,
        margin:float,
        optim_func,
        params:dict,
        lookback_bars:int,
        warmup_bars:int,
        validation_bars:int,
    ):
    
    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
        quit()

    info = mt5.symbol_info(ticker)
    contract_volume = info.trade_contract_size
    minimum_lot = info.volume_min
    pip_value = info.point
    minimum_units = contract_volume * minimum_lot

    minimum_fraction = transformar_a_uno(minimum_units)

    scaled_contract_volume = contract_volume / minimum_fraction

    scaled_pip_value = pip_value * minimum_fraction
    scaled_minimum_units = minimum_lot * scaled_contract_volume
    
    scaled_prices = prices.copy()
    scaled_prices.loc[:, ['Open', 'High', 'Low', 'Close']] = scaled_prices.loc[:, ['Open', 'High', 'Low', 'Close']].copy() * minimum_fraction

    params['minimum_units'] = [scaled_minimum_units]
    params['pip_value'] = [scaled_pip_value]
    params['maximize'] = optim_func
    
    wfo_stats = walk_forward(
        strategy,
        scaled_prices, 
        lookback_bars=lookback_bars,
        validation_bars=validation_bars,
        warmup_bars=warmup_bars, 
        params=params,
        commission=commission, 
        margin=margin, 
        cash=initial_cash,
        verbose=False
    )
    
    df_equity = wfo_stats['_equity']
    df_trades = wfo_stats['_trades']
        
    plot_full_equity_curve(df_equity, title=f'{ticker}, {interval}')        
    
    # Calculo el stability ratio
    x = np.arange(df_equity.shape[0]).reshape(-1, 1)
    reg = LinearRegression().fit(x, df_equity.Equity)
    stability_ratio = reg.score(x, df_equity.Equity)
    
    # Extraigo metricas
    df_stats = pd.DataFrame({
        'strategy':[strategy.__name__],
        'ticker':[ticker],
        'interval':[interval],
        'stability_ratio':[stability_ratio],
        'return':[wfo_stats['Return [%]']],
        'final_eq':[wfo_stats['Equity Final [$]']],
        'drawdown':[wfo_stats['Max. Drawdown [%]']],
        'drawdown_duration':[wfo_stats['Max. Drawdown Duration']],
        'win_rate':[wfo_stats['Win Rate [%]']], 
        'sharpe_ratio':[wfo_stats['Sharpe Ratio']],
        'trades':[df_trades.shape[0]],
        'avg_trade_percent':[wfo_stats['Avg. Trade [%]']],
        'exposure':[wfo_stats['Exposure Time [%]']],
        'final_equity':[wfo_stats['Equity Final [$]']],
        'Duration':[wfo_stats['Duration']],

    })
    
    return wfo_stats, df_stats

def run_strategy(
        strategy,
        ticker,
        interval,
        prices: pd.DataFrame, 
        initial_cash:float,
        commission:float,
        margin:float,
        plot=False
    ):

    
    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
        quit()

    info = mt5.symbol_info(ticker)
    contract_volume = info.trade_contract_size
    minimum_lot = info.volume_min
    pip_value = info.point
    minimum_units = contract_volume * minimum_lot

    minimum_fraction = transformar_a_uno(minimum_units)

    scaled_contract_volume = contract_volume / minimum_fraction

    scaled_pip_value = pip_value * minimum_fraction
    scaled_minimum_units = minimum_lot * scaled_contract_volume
    
    scaled_prices = prices.copy()
    scaled_prices.loc[:, ['Open', 'High', 'Low', 'Close']] = scaled_prices.loc[:, ['Open', 'High', 'Low', 'Close']].copy() * minimum_fraction

    bt_train = Backtest(
        scaled_prices, 
        strategy,
        commission=commission,
        cash=initial_cash, 
        margin=margin
    )
    
    stats = bt_train.run(
        pip_value = scaled_pip_value,
        minimum_units = scaled_minimum_units,
        minimum_fraction = minimum_fraction,
    )
    
    if plot:
        bt_train.plot(filename=f'./plots/{ticker}.html', resample=False)
        
    
    equity_curve = stats._equity_curve['Equity'].values    
    x = np.arange(len(equity_curve)).reshape(-1, 1)
    reg = LinearRegression().fit(x, equity_curve)
    stability_ratio = reg.score(x, equity_curve)

    df_stats = pd.DataFrame({
        'strategy':[strategy.__name__],
        'ticker':[ticker],
        'interval':[interval],
        'stability_ratio':[stability_ratio],
        'return':[stats['Return [%]']],
        'final_eq':[stats['Equity Final [$]']],
        'drawdown':[stats['Max. Drawdown [%]']],
        'drawdown_duration':[stats['Max. Drawdown Duration']],
        'win_rate':[stats['Win Rate [%]']], 
        'sharpe_ratio':[stats['Sharpe Ratio']],
        'trades':[stats['# Trades']],
        'avg_trade_percent':[stats['Avg. Trade [%]']],
        'exposure':[stats['Exposure Time [%]']],
        'final_equity':[stats['Equity Final [$]']],
        'Duration':[stats['Duration']],

    })
    
    return df_stats


def optim_func_2(stats):
    equity_curve = stats._equity_curve['Equity'].values    
    x = np.arange(len(equity_curve)).reshape(-1, 1)
    reg = LinearRegression().fit(x, equity_curve)
    stability_ratio = reg.score(x, equity_curve)
    
    return (stats['Return [%]'] /  (1 + (-1*stats['Max. Drawdown [%]']))) * np.log(1 + stats['# Trades']) * stability_ratio
    
