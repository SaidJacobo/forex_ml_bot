
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

class DemaSuperTrend(Strategy):
    pip_value = None
    minimum_units = None
    maximum_units = None
    contract_volume = None
    opt_params = None
    
    supertrend_length = 7
    supertrend_multiplier = 3
    exit_method = 'bbands'
    dema_period = 200
    risk = 1
    atr_multiplier = 1.5
    bbands_timeperiod = 50
    bband_std = 1.5
    
    def init(self):
        self.dema = self.I(ta.DEMA, self.data.Close, timeperiod=self.dema_period)
        self.atr = self.I(ta.ATR, self.data.High, self.data.Low, self.data.Close)
        
        self.supertrend_signal = self.I(
            super_trend_indicator, 
            self.data.High, 
            self.data.Low, 
            self.data.Close, 
            lenght=self.supertrend_length, 
            multiplier=self.supertrend_multiplier
        )
        
        self.upper_band, self.middle_band, self.lower_band = self.I(
            ta.BBANDS, self.data.Close, 
            timeperiod=self.bbands_timeperiod, 
            nbdevup=self.bband_std, 
            nbdevdn=self.bband_std
        )
        
    def next(self):
        
        actual_date = self.data.index[-1]
        st_buy_signal = self.supertrend_signal[-1] == 1 and self.supertrend_signal[-2] == -1
        st_sell_signal = self.supertrend_signal[-1] == -1 and self.supertrend_signal[-2] == 1
        
        if self.opt_params and actual_date in self.opt_params.keys():
            for k, v in self.opt_params[actual_date].items():
                setattr(self, k, v)

        actual_close = self.data.Close[-1]

        if self.position:
            if self.exit_method == 'super_trend':
                if self.position.is_long and st_sell_signal:
                    self.position.close()

                if self.position.is_short and st_buy_signal:
                    self.position.close()
                
            if self.exit_method == 'bbands':
                if self.position.is_long and crossover(self.data.Close, self.upper_band):
                    self.position.close()

                if self.position.is_short and crossover(self.upper_band, self.data.Close):
                    self.position.close() 
        
        else:
            
            if actual_close > self.dema[-1] and st_buy_signal:
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
                    pip_value=self.pip_value,
                    maximum_units=self.maximum_units,
                    minimum_units=self.minimum_units
                )
                               
                self.buy(
                    size=units,
                    sl=sl_price
                )

            if actual_close < self.dema[-1] and st_sell_signal:
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
                    pip_value=self.pip_value,
                    maximum_units=self.maximum_units,
                    minimum_units=self.minimum_units
                )
                               
                self.sell(
                    size=units,
                    sl=sl_price
                )
    