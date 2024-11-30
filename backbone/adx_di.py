import talib as ta
from backbone.trader_bot import TraderBot
from backtesting import Strategy
from backtesting.lib import crossover
import numpy as np
import MetaTrader5 as mt5
import numpy as np
import pandas as pd

from backbone.utils.general_purpose import calculate_units_size, diff_pips


class AdxDi(Strategy):
    pip_value = None
    minimum_units = None
    maximum_units = None
    contract_volume = None
    opt_params = None
    risk=1
    
    adx_threshold = 25
    atr_multiplier = 2


    def init(self):
        self.plus_di = self.I(ta.PLUS_DI, self.data.High, self.data.Low, self.data.Close, timeperiod=14)
        self.minus_di = self.I(ta.MINUS_DI, self.data.High, self.data.Low, self.data.Close, timeperiod=14)
        self.adx = self.I(ta.ADX, self.data.High, self.data.Low, self.data.Close, timeperiod=14)
        self.atr = self.I(ta.ATR, self.data.High, self.data.Low, self.data.Close)
        
        
    def next(self):
        
        actual_date = self.data.index[-1]
        
        if self.opt_params and actual_date in self.opt_params.keys():
            for k, v in self.opt_params[actual_date].items():
                setattr(self, k, v)

        actual_close = self.data.Close[-1]
    
        if self.position:
            if self.position.is_long:
                if self.adx[-1] < self.adx_threshold or self.plus_di[-1] < self.minus_di[-1]:
                    self.position.close()

            if self.position.is_short:
                if self.adx[-1] < self.adx_threshold or self.plus_di[-1] > self.minus_di[-1]:
                    self.position.close()

        else:

            if self.adx[-1] >= self.adx_threshold and self.plus_di[-1] > self.minus_di[-1]:        
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
                
            if self.adx[-1] >= self.adx_threshold and self.plus_di[-1] < self.minus_di[-1]:        
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
                
    def next_live(self, trader:TraderBot):
        
        open_positions = trader.get_open_positions()
        
        if open_positions:
            if open_positions[-1].type == mt5.ORDER_TYPE_BUY:
                if self.adx[-1] < self.adx_threshold or self.plus_di[-1] < self.minus_di[-1]:
                    trader.close_order(open_positions[-1])

            if open_positions[-1].type == mt5.ORDER_TYPE_SELL:
                if self.adx[-1] < self.adx_threshold or self.plus_di[-1] > self.minus_di[-1]:
                    trader.close_order(open_positions[-1])

        else:
            info_tick = trader.get_info_tick()

            if self.adx[-1] >= self.adx_threshold and self.plus_di[-1] > self.minus_di[-1]:        
                price = info_tick.ask
                
                sl_price = price - self.atr_multiplier * self.atr[-1]
                
                pip_distance = diff_pips(
                    price, 
                    sl_price, 
                    pip_value=self.pip_value
                )
                
                size = calculate_units_size(
                    account_size=trader.equity, 
                    risk_percentage=self.risk, 
                    stop_loss_pips=pip_distance, 
                    pip_value=self.pip_value,
                    maximum_units=self.maximum_units,
                    minimum_units=self.minimum_units, 
                    return_lots=True, 
                    contract_volume=self.contract_volume
                )

                trader.open_order(
                    type_='buy',
                    price=price,
                    size=size, 
                    sl=sl_price
                ) 
                
            if self.adx[-1] >= self.adx_threshold and self.plus_di[-1] < self.minus_di[-1]:        
                price = info_tick.bid
                
                sl_price = price + self.atr_multiplier * self.atr[-1]
                
                pip_distance = diff_pips(
                    price, 
                    sl_price, 
                    pip_value=self.pip_value
                )
                
                size = calculate_units_size(
                    account_size=trader.equity, 
                    risk_percentage=self.risk, 
                    stop_loss_pips=pip_distance, 
                    pip_value=self.pip_value,
                    maximum_units=self.maximum_units,
                    minimum_units=self.minimum_units, 
                    return_lots=True, 
                    contract_volume=self.contract_volume
                )
                
                trader.open_order(
                    type_='sell',
                    price=price,
                    sl=sl_price,
                    size=size
                )