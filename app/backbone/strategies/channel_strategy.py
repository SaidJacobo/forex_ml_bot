import talib as ta
from backbone.trader_bot import TraderBot
from backtesting import Strategy
from backtesting.lib import crossover
import numpy as np
import MetaTrader5 as mt5
import numpy as np

from backbone.utils.general_purpose import calculate_units_size, diff_pips


class Channel(Strategy):
    pip_value = None
    minimum_lot = None
    maximum_lot = None
    contract_volume = None
    trade_tick_value_loss = None
    opt_params = None
    volume_step = None
    risk=None
    
    sma_period = 26
    atr_multiplier = 1.5
    
    def init(self):
        self.sma_200 = self.I(ta.SMA, self.data.Close, timeperiod=200)
        self.atr = self.I(ta.ATR, self.data.High, self.data.Low, self.data.Close)
        
    def next(self):
        actual_date = self.data.index[-1]
        
        if self.opt_params and actual_date in self.opt_params.keys():
            for k, v in self.opt_params[actual_date].items():
                setattr(self, k, v)
            
        self.sma_upper_channel = ta.SMA(self.data.High, timeperiod=self.sma_period)
        self.sma_lower_channel = ta.SMA(self.data.Low, timeperiod=self.sma_period)
        
        if self.position:
            if self.position.is_long:
                if crossover(self.sma_lower_channel, self.data.Close):
                    self.position.close()

            if self.position.is_short:
                if crossover(self.data.Close, self.sma_upper_channel):
                    self.position.close()

        else:
            price = self.data.Close[-1]

            if price > self.sma_200[-1] and crossover(self.data.Close, self.sma_upper_channel):
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
                
            if price < self.sma_200[-1] and crossover(self.sma_lower_channel, self.data.Close):
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
                
                
    def next_live(self, trader:TraderBot):
        actual_date = self.data.index[-1]
        actual_close = self.data.Close[-1]
        
        open_positions = trader.get_open_positions()
        
        if self.opt_params and actual_date in self.opt_params.keys():
            for k, v in self.opt_params[actual_date].items():
                setattr(self, k, v)
            
        self.sma_upper_channel = ta.SMA(self.data.High, timeperiod=self.sma_period)
        self.sma_lower_channel = ta.SMA(self.data.Low, timeperiod=self.sma_period)
        
        actual_close = self.data.Close[-1]
        
        if open_positions:
            if open_positions[-1].type == mt5.ORDER_TYPE_BUY:
                if crossover(self.sma_lower_channel, self.data.Close):
                    trader.close_order(open_positions[-1])

            if open_positions[-1].type == mt5.ORDER_TYPE_SELL:
                if crossover(self.data.Close, self.sma_upper_channel):
                    trader.close_order(open_positions[-1])

        else:
            info_tick = trader.get_info_tick()

            if actual_close > self.sma_200[-1] and crossover(self.data.Close, self.sma_upper_channel):
                price = info_tick.ask * trader.minimum_fraction
                
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
                    maximum_lot=self.maximum_lot,
                    minimum_lot=self.minimum_lot, 
                    return_lots=True, 
                    contract_volume=self.contract_volume,
                    trade_tick_value_loss=self.trade_tick_value_loss,
                    volume_step = trader.volume_step
                )

                trader.open_order(
                    type_='buy',
                    price=price / trader.minimum_fraction, # <-- minimum fraction
                    size=size, 
                    sl=sl_price  / trader.minimum_fraction
                )
                
            if actual_close < self.sma_200[-1] and crossover(self.sma_lower_channel, self.data.Close):
                price = info_tick.bid * trader.minimum_fraction
                
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
                    maximum_lot=self.maximum_lot,
                    minimum_lot=self.minimum_lot, 
                    return_lots=True, 
                    contract_volume=self.contract_volume,
                    trade_tick_value_loss=self.trade_tick_value_loss,
                    volume_step = trader.volume_step
                )
                
                trader.open_order(
                    type_='sell',
                    price=price / trader.minimum_fraction, # <-- minimum fraction
                    size=size, 
                    sl=sl_price  / trader.minimum_fraction
                )