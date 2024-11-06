# %% [markdown]
# # Data

# %%
import os
import sys
root_dir = os.path.abspath(os.path.join(os.path.dirname('../full_portfolio_analysis.ipynb'), '..'))
os.chdir(root_dir)
sys.path.insert(0, os.path.join(root_dir, 'src'))

# %%
from backbone.utils.wfo_utils import run_strategy, run_wfo
from backbone.utils.general_purpose import calculate_units_size, diff_pips

import itertools
import numpy as np
import pandas as pd
import pandas_ta as pandas_ta
import MetaTrader5 as mt5
import MetaTrader5 as mt5
import pandas as pd
from backtest.get_data import get_data
import pytz
from datetime import datetime
from pandas import Timestamp
import numpy as np
import random
from backtesting import Strategy
from backtesting.lib import crossover
import talib as ta

random.seed(42)

# %%
INITIAL_CASH = 10_000
MARGIN = 1/30
COMMISSION = 7e-4

timezone = pytz.timezone("Etc/UTC")
date_from_get_data = datetime(2021, 10, 1, tzinfo=timezone)
date_to_get_data = datetime(2024, 9, 1, tzinfo=timezone)


limited_testing_start_date = Timestamp('2022-01-01 00:00:00', tz='UTC')
limited_testing_end_date = Timestamp('2024-09-01 00:00:00', tz='UTC')

# %%

groups = [
    'Forex_Indicator',
    'CryptoCross_grp',
    'Crypto_group',
    'Energies_group',
    'Forex_group',
    'Indices_group',
    'Stocks_group'
]

# %%
if not mt5.initialize():
    print("initialize() failed, error code =",mt5.last_error())
    quit()

symbols = mt5.symbols_get()

# tickers = [symbol.path.split('\\')[1] for symbol in symbols if ('Stocks_group' in symbol.path or 'Energies_group' in symbol.path or 'Indices_group' in symbol.path)]

tickers = ['US500m']

print(tickers)

intervals = [
    mt5.TIMEFRAME_H4,
]

symbols = get_data(tickers, intervals, date_from_get_data, date_to_get_data)

# %%
max_start_date = None
intervals_start_dates = {}

tickers = np.unique(list(symbols.keys())).tolist()

for interval in intervals:
    for ticker in tickers:
        if not max_start_date or symbols[ticker][interval].index.min() > max_start_date:
            max_start_date = symbols[ticker][interval].index.min()
        
    intervals_start_dates[interval] = max_start_date


intervals_start_dates


print(intervals_start_dates)
print(limited_testing_start_date)
print(limited_testing_end_date)

# %% [markdown]
# # Estrategia

# %%
class BPercent(Strategy):
    pip_value = None
    minimum_units = None
        
    risk= 1
    bbands_timeperiod = 50
    bband_std = 1.5
    sma_period = 200
    b_open_threshold = 0.90
    b_close_threshold = 0.5
    atr_multiplier = 1.8
    pip_value = 0.1

    def init(self):
        
        self.sma = self.I(
            ta.SMA, self.data.Close, timeperiod=self.sma_period
        )

        self.upper_band, self.middle_band, self.lower_band = self.I(
            ta.BBANDS, self.data.Close, 
            timeperiod=self.bbands_timeperiod, 
            nbdevup=self.bband_std, 
            nbdevdn=self.bband_std
        )
        
        self.atr = self.I(ta.ATR, self.data.High, self.data.Low, self.data.Close)
        

    def next(self):
        actual_close = self.data.Close[-1]
        b_percent = (actual_close - self.lower_band[-1]) / (self.upper_band[-1] - self.lower_band[-1])
        
        if self.position:
            if self.position.is_long:
                if b_percent >= self.b_close_threshold:
                    self.position.close()

            if self.position.is_short:
                if b_percent <= 1 - self.b_close_threshold:
                    self.position.close()

        else:
            if b_percent <= 1 - self.b_open_threshold and actual_close > self.sma[-1]:

                sl_price = self.data.Close[-1] - self.atr_multiplier * self.atr[-1]
                
                pip_distance = diff_pips(
                    self.data.Close[-1], 
                    sl_price, 
                    pip_value=self.pip_value
                )
                
                units = calculate_units_size(
                    account_size=self.equity, 
                    risk_percentage=self.risk, 
                    stop_loss_pips=pip_distance, 
                    pip_value=self.pip_value
                )
                
                units = self.minimum_units if units < self.minimum_units else units
                
                self.buy(
                    size=units,
                    sl=sl_price
                )
                
            if b_percent >= self.b_open_threshold and actual_close < self.sma[-1]:
                sl_price = self.data.Close[-1] + self.atr_multiplier * self.atr[-1]
                
                pip_distance = diff_pips(
                    self.data.Close[-1], 
                    sl_price, 
                    pip_value=self.pip_value
                )
                
                units = calculate_units_size(
                    account_size=self.equity, 
                    risk_percentage=self.risk, 
                    stop_loss_pips=pip_distance, 
                    pip_value=self.pip_value
                )
                
                units = self.minimum_units if units < self.minimum_units else units

                self.sell(
                    size=units,
                    sl=sl_price    
                )
    
STRATEGY = BPercent

# %% [markdown]
# # Analisis preliminar

# %%
strategies = [
    STRATEGY
]

experiments = list(itertools.product(
    tickers, intervals, strategies
))

performance = pd.DataFrame()

for ticker, interval, strategy in experiments:
    try:
        print(ticker, interval)
        
        prices = symbols[ticker][interval].loc[limited_testing_start_date:limited_testing_end_date]

        df_stats = run_strategy(
            strategy=strategy,
            ticker=ticker,
            interval=interval,
            commission=COMMISSION, 
            prices=prices, 
            initial_cash=INITIAL_CASH, 
            margin=MARGIN
        )

        performance = pd.concat([performance, df_stats])

    except Exception as e:
        print(f'hubo un problema con {ticker} {interval}: {e}')


performance['return/dd'] = performance['return'] / -performance['drawdown']
performance['drawdown'] = -performance['drawdown']
performance['custom_metric'] = (performance['return'] / (1 + performance.drawdown)) * np.log(1 + performance.trades)


# %%

filter_performance = performance[
    # (performance['ticker'] == 'USOILm')
    (performance['return/dd']>2)
    & (performance['stability_ratio']>0.7)
].sort_values(by=['custom_metric'], ascending=[False]).drop_duplicates(subset=['ticker'], keep='first')

portfolio = filter_performance.ticker.tolist()
intervals = filter_performance.interval.values.tolist()


# portfolio


# %%
# for ticker, interval in zip(portfolio, intervals):
    
#     prices = symbols[ticker][interval]

    
#     df_stats = run_strategy(
#         strategy=strategy,
#         ticker=ticker,
#         interval=interval,
#         commission=COMMISSION, 
#         prices=prices, 
#         initial_cash=INITIAL_CASH, 
#         margin=MARGIN,
#         plot=True
#     )


# %% [markdown]
# # WFO

# %%
from backbone.utils.wfo_utils import optim_func_2

lookback_bars = 1800
validation_bars = 180
warmup_bars = 200

all_wfo_performances = pd.DataFrame()
stats_per_symbol = {}

params = {
    'b_open_threshold' : [0.9, 0.95, 1, 1.5],
    'b_close_threshold': [0.5, 0.6, 0.8, 0.9, 1],
}

for index, row in filter_performance.iterrows():
    
    try:
        ticker = row.ticker
        interval = row.interval
        
        print(ticker, interval)
        
        prices = symbols[ticker][interval]

        wfo_stats, df_stats = run_wfo(
            strategy=STRATEGY,
            ticker=ticker,
            interval=interval,
            prices=prices,
            initial_cash=INITIAL_CASH,
            commission=COMMISSION,
            margin=MARGIN,
            optim_func=optim_func_2,
            params=params,
            lookback_bars=lookback_bars,
            warmup_bars=warmup_bars,
            validation_bars=validation_bars
        )
        
        if ticker not in stats_per_symbol.keys():
            stats_per_symbol[ticker] = {}

        stats_per_symbol[ticker][interval] = wfo_stats

        all_wfo_performances = pd.concat([all_wfo_performances, df_stats])
    
    except:
        print(f'No se pudo ejecutar para el ticker {ticker}')

all_wfo_performances['return/dd'] = all_wfo_performances['return'] / -all_wfo_performances['drawdown']
all_wfo_performances['drawdown'] = -all_wfo_performances['drawdown']
all_wfo_performances['custom_metric'] = (all_wfo_performances['return'] / (1 + all_wfo_performances.drawdown)) * np.log(1 + all_wfo_performances.trades)

all_wfo_performances.drawdown_duration = pd.to_timedelta(all_wfo_performances.drawdown_duration)
all_wfo_performances.drawdown_duration = all_wfo_performances.drawdown_duration.dt.days

all_wfo_performances.sort_values(by='return/dd', ascending=False)

# %%
all_wfo_performances[
    (all_wfo_performances['return/dd'] > 1)
    
].sort_values(by='custom_metric', ascending=False)

# %% [markdown]
# # Montecarlo

# %%
filtered_wfo_performance = all_wfo_performances[
    (all_wfo_performances['stability_ratio'] > 0.7)
].sort_values(by='return/dd', ascending=False)

filtered_wfo_performance

# %%
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from backbone.utils.wfo_utils import montecarlo_statistics_simulation

# Crear una lista para almacenar los resultados de cada ticker
data_drawdown = []
data_return = []
montecarlo_simulations = {}

all_drawdowns = pd.DataFrame()
all_returns = pd.DataFrame()

for index, row in filtered_wfo_performance.iterrows():
    ticker = row.ticker
    interval = row.interval
    
    print(f"Procesando ticker: {ticker}")
    trades_history = stats_per_symbol[ticker][interval]._trades
    eq_curve = stats_per_symbol[ticker][interval]._equity_curve
    
    # Simulación de Montecarlo para cada ticker (datos agregados)
    mc, synthetic_drawdown_curve, synthetic_return_curve = montecarlo_statistics_simulation(
        equity_curve=eq_curve,
        trade_history=trades_history, 
        n_simulations=100_000, 
        initial_equity=INITIAL_CASH, 
        threshold_ruin=0.8, 
        return_raw_curves=True,
        percentiles=[0.1, 0.25, 0.5, 0.75, 0.9]
    )
    
    montecarlo_simulations[ticker] = mc
    
    synthetic_drawdown_curve['ticker'] = ticker
    synthetic_return_curve['ticker'] = ticker
    
    all_drawdowns = pd.concat([all_drawdowns, synthetic_drawdown_curve])
    all_returns = pd.concat([all_returns, synthetic_return_curve])

# %%
dd_df = pd.DataFrame()
returns_df = pd.DataFrame()

for ticker, mc in montecarlo_simulations.items():
    mc = mc.rename(
        columns={
            'Drawdown (%)': f'drawdown_{ticker}',
            'Final Return (%)': f'return_{ticker}',
        }
    )

    if dd_df.empty:
        dd_df = mc[[f'drawdown_{ticker}']]
    
    else:
        dd_df = pd.merge(
            dd_df,
            mc[[f'drawdown_{ticker}']],
            left_index=True,
            right_index=True            
        )
        
    if returns_df.empty:
        returns_df = mc[[f'return_{ticker}']]
    
    else:
        returns_df = pd.merge(
            returns_df,
            mc[[f'return_{ticker}']],
            left_index=True,
            right_index=True            
        )
        

# %%
# Configurar el gráfico con matplotlib y seaborn
plt.figure(figsize=(25, 18))
sns.boxplot(data=all_drawdowns, x="ticker", y="Drawdown (%)")
plt.title("Comparación de Drawdown (%) entre Tickers")

y_max = all_drawdowns["Drawdown (%)"].max()  # Valor máximo en el eje Y
y_min = all_drawdowns["Drawdown (%)"].min()  # Valor mínimo en el eje Y
tick_interval = 2  # Intervalo deseado entre números en el eje Y

# Configurar los ticks mayores en el eje Y
plt.yticks(np.arange(y_min, y_max + tick_interval, tick_interval))

# Activar la cuadrícula
plt.grid(True, linestyle='--', which='both', color='grey', alpha=0.7)

# Mostrar el gráfico
plt.show()


# %%
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Generar el gráfico
plt.figure(figsize=(12, 20))
sns.boxplot(data=all_returns, x="ticker", y="Final Return (%)")
plt.title("Comparación de Retorno (%) entre Tickers")

# Configurar ticks mayores con más números
y_max = all_returns["Final Return (%)"].max()  # Valor máximo en el eje Y
y_min = all_returns["Final Return (%)"].min()  # Valor mínimo en el eje Y
tick_interval = 10  # Intervalo deseado entre números en el eje Y

# Configurar los ticks mayores en el eje Y
plt.yticks(np.arange(y_min, y_max + tick_interval, tick_interval))

# Activar la cuadrícula
plt.grid(True, linestyle='--', which='both', color='grey', alpha=0.7)

# Mostrar el gráfico
plt.show()


# %%



