import talib as ta
from backbone.trader_bot import TraderBot
from backtesting import Strategy
from backtesting.lib import crossover
import numpy as np
import MetaTrader5 as mt5
import numpy as np
import pandas as pd

from backbone.utils.general_purpose import calculate_units_size, diff_pips


class RandomTrader(Strategy):
    pip_value = None
    minimum_lot = None
    maximum_lot = None
    contract_volume = None
    trade_tick_value_loss = None
    opt_params = None
    volume_step = None
    risk=1
    
    prob_trade = 0.5
    prob_long = 0.5
    prob_short = 0.5
    avg_position_hold = 2
    std_position_hold = 1.5
    
    pos_hold = 0
    max_pos_hold = 0
    
    atr_multiplier = 1.5

    def init(self):
        self.atr = self.I(ta.ATR, self.data.High, self.data.Low, self.data.Close)
        
        if self.opt_params:
            for k, v in self.opt_params.items():
                setattr(self, k, v)
        
        
    def next(self):
    
        if self.position:
            self.pos_hold += 1
            
            if self.pos_hold >= self.max_pos_hold:
                self.position.close()
                self.pos_hold = 0

        else:
            trade = None
            long = None
            short = None

            if np.random.rand() < self.prob_trade:
                trade = True
                if np.random.rand() < self.prob_long:
                    long = True
                else:
                    short = True
            
            price = self.data.Close[-1]

            if trade and long:        
                sl_price = self.data.Close[-1] - self.atr_multiplier * self.atr[-1]
                
                pip_distance = diff_pips(
                    price, 
                    sl_price, 
                    pip_value=self.pip_value
                )
                
                units = calculate_units_size(
                    account_size=self.equity, 
                    risk_percentage=self.risk, 
                    stop_loss_pips=pip_distance, 
                    maximum_lot=self.maximum_lot,
                    minimum_lot=self.minimum_lot, 
                    return_lots=False, 
                    contract_volume=self.contract_volume,
                    trade_tick_value_loss=self.trade_tick_value_loss
                )
                
                self.buy(
                    size=units,
                    sl=sl_price
                )
                
                self.max_pos_hold = np.round(np.random.normal(self.avg_position_hold, self.std_position_hold, 1)[0])
                
            if trade and short:        
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
                    maximum_lot=self.maximum_lot,
                    minimum_lot=self.minimum_lot, 
                    return_lots=False, 
                    contract_volume=self.contract_volume,
                    trade_tick_value_loss=self.trade_tick_value_loss
                )
                
                self.sell(
                    size=units,
                    sl=sl_price
                )
                
                self.max_pos_hold = np.round(np.random.normal(self.avg_position_hold, self.std_position_hold, 1)[0])
                
                
    