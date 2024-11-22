from backtesting import Strategy
from backtesting.lib import crossover
import talib as ta
import numpy as np
import MetaTrader5 as mt5
from backbone.trader_bot import TraderBot
from backbone.utils.general_purpose import calculate_units_size, diff_pips
import pandas_ta
import pandas as pd


def super_trend_indicator(high, low, close, lenght=7, multiplier=3):
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)
    
    sti = pandas_ta.supertrend(high, low, close, length=lenght, multiplier=multiplier)
    
    return sti[f'SUPERTd_{lenght}_{multiplier}.0']

class TripleSuperTrend(Strategy):
    pip_value = None
    minimum_units = None
    maximum_units = None
    contract_volume = None
    opt_params = None
    
    risk = 1
    atr_multiplier = 1.5

    
    def init(self):
        self.atr = self.I(ta.ATR, self.data.High, self.data.Low, self.data.Close)
        
        self.supertrend_signal_123 = self.I(super_trend_indicator, self.data.High, self.data.Low, self.data.Close, lenght=12, multiplier=3)
        self.supertrend_signal_101 = self.I(super_trend_indicator, self.data.High, self.data.Low, self.data.Close, lenght=10, multiplier=1)
        self.supertrend_signal_112 = self.I(super_trend_indicator, self.data.High, self.data.Low, self.data.Close, lenght=11, multiplier=2)
        
    def next(self):
        
        st_buy_signal = self.supertrend_signal_123[-1] == 1 and self.supertrend_signal_101[-1] == 1 and self.supertrend_signal_112[-1] == 1
        st_sell_signal = self.supertrend_signal_123[-1] == -1 and self.supertrend_signal_101[-1] == -1 and self.supertrend_signal_112[-1] == -1
        

        if self.position:
            if self.position.is_long and not st_buy_signal:
                self.position.close()

            if self.position.is_short and not st_sell_signal:
                self.position.close()
        
        else:
            price = self.data.Close[-1]
            
            if st_buy_signal:
                sl_price = price - self.atr_multiplier * self.atr[-1]
                pip_distance = diff_pips(
                    price, 
                    sl_price, 
                    pip_value=self.pip_value
                )
                
                units = calculate_units_size(
                    account_size=self.equity, 
                    risk_percentage=self.risk, 
                    stop_loss_pips=pip_distance, 
                    pip_value=self.pip_value,
                    maximum_units=self.maximum_units,
                    minimum_units=self.minimum_units
                )
                               
                self.buy(
                    size=units,
                    sl=sl_price
                )

            if st_sell_signal:
                sl_price = price + self.atr_multiplier * self.atr[-1]
                
                pip_distance = diff_pips(
                    price, 
                    sl_price, 
                    pip_value=self.pip_value
                )
                
                units = calculate_units_size(
                    account_size=self.equity, 
                    risk_percentage=self.risk, 
                    stop_loss_pips=pip_distance, 
                    pip_value=self.pip_value,
                    maximum_units=self.maximum_units,
                    minimum_units=self.minimum_units
                )
                               
                self.sell(
                    size=units,
                    sl=sl_price
                )