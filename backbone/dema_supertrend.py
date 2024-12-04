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

class DemaSuperTrend2(Strategy):
    pip_value = None
    minimum_lot = None
    maximum_lot = None
    contract_volume = None
    trade_tick_value_loss = None
    opt_params = None
    risk=1
    
    dema_period = 200
    atr_multiplier = 1.5
    super_trend_to_use = 'supertrend_signal_73' # <-- parametro a optimizar

    
    def init(self):
        self.dema = self.I(ta.DEMA, self.data.Close, timeperiod=self.dema_period)
        self.atr = self.I(ta.ATR, self.data.High, self.data.Low, self.data.Close)
        
        self.supertrend_signal_73 = self.I(super_trend_indicator,self.data.High, self.data.Low, self.data.Close, lenght=7, multiplier=3)
        self.supertrend_signal_123 = self.I(super_trend_indicator,self.data.High, self.data.Low, self.data.Close, lenght=12, multiplier=3)
        self.supertrend_signal_101 = self.I(super_trend_indicator,self.data.High, self.data.Low, self.data.Close, lenght=10, multiplier=1)
        self.supertrend_signal_112 = self.I(super_trend_indicator,self.data.High, self.data.Low, self.data.Close, lenght=11, multiplier=2)
        
    def next(self):
        actual_date = self.data.index[-1]
        
        if self.opt_params and actual_date in self.opt_params.keys():
            for k, v in self.opt_params[actual_date].items():
                setattr(self, k, v)
        
        actual_super_trend = getattr(self, self.super_trend_to_use)
        
        st_buy_signal = actual_super_trend[-1] == 1 and actual_super_trend[-2] == -1
        st_sell_signal = actual_super_trend[-1] == -1 and actual_super_trend[-2] == 1
        
        actual_close = self.data.Close[-1]

        if self.position:
            if self.position.is_long and st_sell_signal:
                self.position.close()

            if self.position.is_short and st_buy_signal:
                self.position.close()
        
        else:
            price = self.data.Close[-1]
            
            if actual_close > self.dema[-1] and st_buy_signal:
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

            if actual_close < self.dema[-1] and st_sell_signal:
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
    
    
    def next_live(self, trader: TraderBot):

        actual_date = self.data.index[-1]
        
        actual_super_trend = getattr(self, self.super_trend_to_use)
        
        st_buy_signal = actual_super_trend[-1] == 1 and actual_super_trend[-2] == -1
        st_sell_signal = actual_super_trend[-1] == -1 and actual_super_trend[-2] == 1
        
        actual_close = self.data.Close[-1]
        open_positions = trader.get_open_positions()

        if open_positions:
            if self.exit_method == "super_trend":
                if open_positions[-1].type == mt5.ORDER_TYPE_BUY and st_sell_signal:
                    trader.close_order(open_positions[-1])
                
                if open_positions[-1].type == mt5.ORDER_TYPE_SELL and st_buy_signal:
                    trader.close_order(open_positions[-1])
                    
            if self.exit_method == "bbands":
                if open_positions[-1].type == mt5.ORDER_TYPE_BUY and crossover(
                    self.data.Close, self.upper_band
                ):
                    trader.close_order(open_positions[-1])
                
                if open_positions[-1].type == mt5.ORDER_TYPE_SELL and crossover(
                    self.lower_band, self.data.Close
                ):
                    trader.close_order(open_positions[-1])
        else:
            if actual_close > self.dema[-1] and st_buy_signal:

                info_tick = trader.get_info_tick()
                price = info_tick.ask

                sl_price = price - self.atr_multiplier * self.atr[-1]

                pip_distance = diff_pips(price, sl_price, pip_value=self.pip_value)

                units = calculate_units_size(
                    account_size=self.equity,
                    risk_percentage=self.risk,
                    stop_loss_pips=pip_distance,
                    pip_value=self.pip_value,
                    maximum_lot=self.maximum_units,
                    minimum_lot=self.minimum_units,
                )

                lots = int((units / self.contract_volume) * 100) / 100

                trader.open_order(type_="buy", price=price, size=lots, sl=sl_price)
            if actual_close < self.dema[-1] and st_sell_signal:

                info_tick = trader.get_info_tick()
                price = info_tick.bid

                sl_price = price + self.atr_multiplier * self.atr[-1]

                pip_distance = diff_pips(price, sl_price, pip_value=self.pip_value)

                units = calculate_units_size(
                    account_size=self.equity,
                    risk_percentage=self.risk,
                    stop_loss_pips=pip_distance,
                    pip_value=self.pip_value,
                    maximum_lot=self.maximum_units,
                    minimum_lot=self.minimum_units,
                )

                lots = int((units / self.contract_volume) * 100) / 100

                trader.open_order(type_="sell", price=price, sl=sl_price, size=lots)