import talib as ta
from backbone.trader_bot import TraderBot
from backtesting import Strategy
from backtesting.lib import crossover
import numpy as np
import MetaTrader5 as mt5
import numpy as np
import pandas as pd

from backbone.utils.general_purpose import calculate_units_size, diff_pips


class TripleSMA(Strategy):
    pip_value = None
    minimum_lot = None
    maximum_lot = None
    contract_volume = None
    trade_tick_value_loss = None
    opt_params = None
    volume_step = None
    risk=1
    
    atr_multiplier = 2

    def init(self):
        self.atr = self.I(ta.ATR, self.data.High, self.data.Low, self.data.Close)
        self.sma_12 = self.I(ta.SMA, self.data.Close, timeperiod=12)
        self.sma_8 = self.I(ta.SMA, self.data.Close, timeperiod=8)
        self.sma_5 = self.I(ta.SMA, self.data.Close, timeperiod=5)
        
        self.sma_200 = self.I(ta.SMA, self.data.Close, timeperiod=200)
        
        
    def next(self):
        
        actual_date = self.data.index[-1]
        
        if self.opt_params and actual_date in self.opt_params.keys():
            for k, v in self.opt_params[actual_date].items():
                setattr(self, k, v)

        price = self.data.Close[-1]
        actual_up_trend = self.sma_5[-1] > self.sma_8[-1] > self.sma_12[-1]
        actual_down_trend = self.sma_5[-1] < self.sma_8[-1] < self.sma_12[-1]
        
        past_up_trend = self.sma_5[-2] > self.sma_8[-2] > self.sma_12[-2]
        past_down_trend = self.sma_5[-2] < self.sma_8[-2] < self.sma_12[-2]
    
        if self.position:
            if self.position.is_long:
                if not actual_up_trend:
                    self.position.close()

            if self.position.is_short:
                if not actual_down_trend:
                    self.position.close()

        else:
            price = self.data.Close[-1]
            
            if (actual_up_trend and not past_up_trend) and price > self.sma_200[-1]:
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
                
            if (actual_down_trend and not past_down_trend) and price < self.sma_200[-1]:
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
        actual_close = self.data.Close[-1]

        actual_up_trend = self.sma_5[-1] > self.sma_8[-1] > self.sma_12[-1]
        actual_down_trend = self.sma_5[-1] < self.sma_8[-1] < self.sma_12[-1]
        
        past_up_trend = self.sma_5[-2] > self.sma_8[-2] > self.sma_12[-2]
        past_down_trend = self.sma_5[-2] < self.sma_8[-2] < self.sma_12[-2]
    
        open_positions = trader.get_open_positions()
    
        if open_positions:
            if open_positions[-1].type == mt5.ORDER_TYPE_BUY:
                if not actual_up_trend:
                    trader.close_order(open_positions[-1])

            if open_positions[-1].type == mt5.ORDER_TYPE_SELL:
                if not actual_down_trend:
                    trader.close_order(open_positions[-1])

        else:
            info_tick = trader.get_info_tick()

            if (actual_up_trend and not past_up_trend) and actual_close > self.sma_200[-1]:
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
                
            if (actual_down_trend and not past_down_trend) and actual_close < self.sma_200[-1]:
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
                