from backtesting import Strategy
import talib as ta
import numpy as np
import MetaTrader5 as mt5
from backbone.trader_bot import TraderBot
from backbone.utils.general_purpose import calculate_units_size, diff_pips

np.seterr(divide='ignore')

class MeanReversion(Strategy):
    pip_value = None
    minimum_lot = None
    maximum_lot = None
    contract_volume = None
    trade_tick_value_loss = None
    opt_params = None
    risk=1
    
    sma_period = 50
    deviation_threshold = 0.1
    cum_rsi_up_threshold = 90
    cum_rsi_down_threshold = 10
    atr_multiplier = 2
    
    def init(self):
        self.sma = self.I(ta.SMA, self.data.Close, timeperiod=self.sma_period)
        self.rsi = self.I(ta.RSI, self.data.Close, timeperiod=2)
        self.atr = self.I(ta.ATR, self.data.High, self.data.Low, self.data.Close)
        
    def next(self):
        
        actual_date = self.data.index[-1]
        
        if self.opt_params and actual_date in self.opt_params.keys():
            for k, v in self.opt_params[actual_date].items():
                setattr(self, k, v)

        # Precio actual y valor de la SMA
        price = self.data.Close[-1]
        sma_value = self.sma[-1]
        cum_rsi = self.rsi[-1] + self.rsi[-2]

        # Desviación del precio con respecto a la SMA (en porcentaje)
        deviation = (price - sma_value) / sma_value

        if self.position:
            if self.position.is_long and price >= self.sma[-1]:
                self.position.close()

            if self.position.is_short and price <= self.sma[-1]:
                self.position.close() 
        
        else:
            # Condiciones para comprar (precio por debajo de la SMA más del umbral de desviación)
            if deviation <= -self.deviation_threshold and cum_rsi <= self.cum_rsi_down_threshold:
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

            # Condiciones para vender (precio por encima de la SMA más del umbral de desviación)
            elif deviation >= self.deviation_threshold and cum_rsi >= self.cum_rsi_up_threshold:
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
        
        # Precio actual y valor de la SMA
        actual_close = self.data.Close[-1]
        sma_value = self.sma[-1]
        cum_rsi = self.rsi[-1] + self.rsi[-2]
        deviation = (actual_close - sma_value) / sma_value

        open_positions = trader.get_open_positions()

        if open_positions:
            if open_positions[-1].type == mt5.ORDER_TYPE_BUY and actual_close >= self.sma[-1]:
                    trader.close_order(open_positions[-1])

            if open_positions[-1].type == mt5.ORDER_TYPE_SELL and actual_close <= self.sma[-1]:
                    trader.close_order(open_positions[-1])
        
        else:
            # Condiciones para comprar (precio por debajo de la SMA más del umbral de desviación)
            if deviation <= -self.deviation_threshold and cum_rsi <= self.cum_rsi_down_threshold:
                info_tick = trader.get_info_tick()
                price = info_tick.ask
                
                sl_price = price - price * self.atr[-1]
                
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
                    maximum_lot=self.maximum_units,
                    minimum_lot=self.minimum_units
                )
                
                lots = int((units / self.contract_volume) * 100) / 100

                trader.open_order(
                    type_='buy',
                    price=price,
                    size=lots, 
                    sl=sl_price
                )  

            # Condiciones para vender (precio por encima de la SMA más del umbral de desviación)
            elif deviation >= self.deviation_threshold and cum_rsi >= self.cum_rsi_up_threshold:
                info_tick = trader.get_info_tick()
                price = info_tick.bid
                
                sl_price = price + self.atr_multiplier * self.atr[-1]
                
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
                    maximum_lot=self.maximum_units,
                    minimum_lot=self.minimum_units
                )
                
                lots = int((units / self.contract_volume) * 100) / 100
                
                trader.open_order(
                    type_='sell',
                    price=price,
                    sl=sl_price,
                    size=lots
                )