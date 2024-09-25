from datetime import datetime, timedelta
import pandas as pd
import pytz
import talib as ta
import yfinance as yf
import MetaTrader5 as mt5
from backbone.trader_bot import TraderBot
from backtesting import Backtest, Strategy
import numpy as np


def  optim_func(series):
    return (series['Return [%]'] /  (1 + (-1*series['Max. Drawdown [%]']))) * np.log(1 + series['# Trades'])

def ll_hh_indicator(close, window=None):
    if type(close) != pd.Series:
        close = close.s

    rolling_min = close.rolling(window=window, min_periods=1).min()
    is_lower_low = close == rolling_min

    rolling_max = close.rolling(window=window, min_periods=1).max()
    is_higher_high = close == rolling_max

    return is_lower_low, is_higher_high

class VixRsi(Strategy):
    vix_percentage_above_sma = 0.05
    ll_hh_window = 5
    rsi_threshold = 50
    sma_period = 200
    vix_sma_period = 10
    rsi_period = 2
    
    def init(self):
        self.rsi = self.I(ta.RSI, self.data.Close, timeperiod=self.rsi_period)
        self.sma = self.I(ta.SMA, self.data.Close, timeperiod=self.sma_period)
        self.vix_sma = self.I(ta.SMA, self.data.VixClose, timeperiod=self.vix_sma_period)
        self.lower_low, self.higher_high = self.I(ll_hh_indicator, self.data.Close, window=self.ll_hh_window)

    def next(self):
        actual_close = self.data.Close[-1]

        if self.position:
            first_trade = self.trades[0]
            today = self.data.index[-1].tz_convert('UTC')
            time_in_position = (today - first_trade.entry_time.tz_convert('UTC'))
            time_in_position = time_in_position.days

            if self.position.is_long:
                if self.higher_high:
                    self.position.close()

        else:
            cum_rsi = self.rsi[-1] + self.rsi[-2]
            vix_sma_value = self.vix_sma[-1]
            vix_close = self.data.VixClose[-1]
            vix_above_sma = vix_close > (vix_sma_value * (1 + self.vix_percentage_above_sma))

            if vix_above_sma and cum_rsi <= self.rsi_threshold and actual_close > self.sma[-1]:
                self.buy(size=1)
                
    def next_live(self, trader:TraderBot):
        actual_close = self.data.Close[-1]

        positions = trader.get_open_positions()
        if positions and positions[-1].type == mt5.ORDER_TYPE_BUY:
            if self.higher_high:
                trader.close_order(positions[-1])

        else:
            cum_rsi = self.rsi[-1] + self.rsi[-2]

            vix_sma_value = self.vix_sma[-1]
            vix_close = self.data.VixClose[-1]
            vix_above_sma = vix_close > (vix_sma_value * (1 + self.vix_percentage_above_sma))

            if vix_above_sma and cum_rsi <= self.rsi_threshold and actual_close > self.sma[-1]:
                info_tick = trader.get_info_tick()
                price = info_tick.ask
                
                trader.open_order(
                    ticker=self.ticker, 
                    lot=self.lot_size, 
                    type_='buy',
                    price=price
                )


class VixTrader(TraderBot):
    
    def __init__(self, ticker, timeframe, creds, opt_params, wfo_params):
        
        name = f'Vix_{ticker}_{timeframe}'
        self.trader = TraderBot(
            name=name,
            ticker=ticker, 
            timeframe=timeframe, 
            creds=creds
        )
        
        self.opt_params = opt_params
        self.wfo_params = wfo_params
        self.opt_params['maximize'] = optim_func
    
    
    def run(self):
        warmup_bars = self.wfo_params['warmup_bars']
        look_back_bars = self.wfo_params['look_back_bars']

        timezone = pytz.timezone("Etc/UTC")
        now = datetime.now(tz=timezone)
        date_from = now - timedelta(hours=look_back_bars) - timedelta(hours=warmup_bars) 
        
        print(f'excecuting run {self.trader.name} at {now}')
        
        vix = yf.Ticker("^VIX").history(interval='1h', period='1y')
        vix.rename(
            columns={'Close':'VixClose'}, inplace=True
        )

        vix.index = vix.index.tz_convert('UTC')

        df = self.trader.get_data(
            date_from=date_from, 
            date_to=now,
        )

        df.index = df.index.tz_localize('UTC').tz_convert('UTC')

        full_df = pd.merge(
            df, 
            vix[['VixClose']], 
            left_index=True, 
            right_index=True
        )

        bt_train = Backtest(
            full_df, 
            VixRsi,
            commission=7e-4,
            cash=15_000, 
            margin=1/30
        )
        
        stats_training = bt_train.optimize(
            **self.opt_params
        )
        
        bt = Backtest(
            full_df, 
            VixRsi,
            commission=7e-4,
            cash=15_000, 
            margin=1/30
        )
        
        opt_params = {param: getattr(stats_training._strategy, param) for param in self.opt_params.keys() if param != 'maximize'}

        stats = bt.run(
            **opt_params
        )

        bt_train._results._strategy.next_live(trader=self.trader)         

