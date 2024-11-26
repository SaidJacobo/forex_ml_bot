import talib as ta
from backbone.trader_bot import TraderBot
from backtesting import Strategy
from backtesting.lib import crossover
import numpy as np
import MetaTrader5 as mt5
import numpy as np
import pandas as pd

from backbone.utils.general_purpose import calculate_units_size, diff_pips

def ibs_indicator(high, low, close):
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)
    
    ibs = (close - low) / (high - low)
    return ibs
    

class ShortIBS(Strategy):
    pip_value = None
    minimum_units = None
    maximum_units = None
    contract_volume = None
    risk = 1
    opt_params = None
    
    enter_ibs = 0.9
    exit_ibs = 0.3
    atr_multiplier = 1.5
    
    def init(self):
        self.atr = self.I(ta.ATR, self.data.High, self.data.Low, self.data.Close)
        self.sma = self.I(ta.SMA, self.data.Close, timeperiod=200)
        self.ibs = self.I(ibs_indicator, self.data.High, self.data.Low, self.data.Close)
        
    
    def next(self):
        actual_date = self.data.index[-1]
        close = self.data.Close[-1]
        
        actual_ibs = self.ibs[-1]
        
        if self.opt_params and actual_date in self.opt_params.keys():
            for k, v in self.opt_params[actual_date].items():
                setattr(self, k, v)
            
        if self.position:
            if self.position.is_short:
                if actual_ibs <= self.exit_ibs:
                    self.position.close()

        else:
            if close < self.sma[-1] and actual_ibs >= self.enter_ibs:
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