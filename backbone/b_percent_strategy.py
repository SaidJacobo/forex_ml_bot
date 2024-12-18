from backtesting import Strategy
import talib as ta
from backbone.trader_bot import TraderBot
import numpy as np
import MetaTrader5 as mt5
import numpy as np
from backbone.utils.general_purpose import calculate_units_size, diff_pips

np.seterr(divide='ignore')

class BPercent(Strategy):
    pip_value = None
    minimum_lot = None
    maximum_lot = None
    contract_volume = None
    trade_tick_value_loss = None
    opt_params = None
    volume_step = None 
    risk=1
    
    bbands_timeperiod = 50
    bband_std = 1.5
    sma_period = 200
    b_open_threshold = 0.90
    b_close_threshold = 0.5
    atr_multiplier = 2

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
        
        actual_date = self.data.index[-1]
        
        if self.opt_params and actual_date in self.opt_params.keys():
            self.b_open_threshold = self.opt_params[actual_date]['b_open_threshold']
            self.b_close_threshold = self.opt_params[actual_date]['b_open_threshold']
        
        price = self.data.Close[-1]
        b_percent = (price - self.lower_band[-1]) / (self.upper_band[-1] - self.lower_band[-1])
        
        if self.position:
            if self.position.is_long:
                if b_percent >= self.b_close_threshold:
                    self.position.close()

            if self.position.is_short:
                if b_percent <= 1 - self.b_close_threshold:
                    self.position.close()

        else:
            if b_percent <= 1 - self.b_open_threshold and price > self.sma[-1]:
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
                
            if b_percent >= self.b_open_threshold and price < self.sma[-1]:
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
        price = self.data.Close[-1]
        b_percent = (price - self.lower_band[-1]) / (self.upper_band[-1] - self.lower_band[-1])
        
        open_positions = trader.get_open_positions()
        
        if open_positions:
            if open_positions[-1].type == mt5.ORDER_TYPE_BUY:
                if b_percent >= self.b_close_threshold:
                    trader.close_order(open_positions[-1])

            if open_positions[-1].type == mt5.ORDER_TYPE_SELL:
                if b_percent <= 1 - self.b_close_threshold:
                    trader.close_order(open_positions[-1])

        else:
            info_tick = trader.get_info_tick()

            if b_percent <= 1 - self.b_open_threshold and price > self.sma[-1]:
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
                
            if b_percent >= self.b_open_threshold and price < self.sma[-1]:
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