import talib as ta
from backbone.trader_bot import TraderBot
from backtesting import Strategy
import numpy as np
import MetaTrader5 as mt5
from backbone.utils.general_purpose import diff_pips, calculate_units_size


np.seterr(divide='ignore')

class DayPerWeek(Strategy):
    pip_value = None
    minimum_units = None
    maximum_units = None
    contract_volume = None
    
    opt_params = None
    
    risk = 1
    day_to_buy = 3
    percentage_price_sl = 5
    sma_period = 200
    rsi_period = 2
    rsi_upper_threshold = 90
    
    def init(self):
        self.sma = self.I(
            ta.SMA, self.data.Close, timeperiod=self.sma_period
        )

        self.rsi = self.I(
            ta.RSI, self.data.Close, 2
        )
        
    def next(self):
        actual_date = self.data.index[-1]
        
        if self.opt_params and actual_date in self.opt_params.keys():
            for k, v in self.opt_params[actual_date].items():
                setattr(self, k, v)
        
        today = self.data.index[-1]
        if self.position:
            if self.position.is_long:
                if self.rsi > self.rsi_upper_threshold:
                    self.position.close()

        else:
            # es el dia de compra, el precio esta por encima de la sma
            if today.day_of_week == self.day_to_buy and self.data.Close[-1] > self.sma[-1]:
                sl_price = self.data.Close[-1] - self.data.Close[-1] *  (self.percentage_price_sl / 100)
                
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
                    sl=sl_price,
                )
    
    def next_live(self, trader:TraderBot):
        
        open_positions = trader.get_open_positions()
        if open_positions:      
            if open_positions[-1].type == mt5.ORDER_TYPE_BUY:
                if self.rsi[-1] > self.rsi_upper_threshold:
                    trader.close_order(open_positions[-1])

        else:
            today = self.data.index[-1]
            # es el dia de compra, el precio esta por encima de la sma
            if today.day_of_week == self.day_to_buy and self.data.Close[-1] > self.sma[-1]:
                info_tick = trader.get_info_tick()
                price = info_tick.ask
                
                sl_price = price - price * (self.percentage_price_sl / 100)
                
                pip_distance = diff_pips(
                    price, 
                    sl_price, 
                    pip_value=self.pip_value
                )
                
                units = calculate_units_size(
                    account_size=trader.equity, 
                    risk_percentage=self.risk, 
                    stop_loss_pips=pip_distance, 
                    pip_value=self.pip_value,
                    maximum_units=self.maximum_units,
                    minimum_units=self.minimum_units
                )
                
                lots = units / self.contract_volume

                trader.open_order(
                    type_='buy',
                    price=price,
                    size=lots, 
                    sl=sl_price
                )   