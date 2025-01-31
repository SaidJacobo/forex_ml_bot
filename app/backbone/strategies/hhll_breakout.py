import talib as ta
from backbone.trader_bot import TraderBot
from backtesting import Strategy
from backtesting.lib import crossover
import numpy as np
import MetaTrader5 as mt5
from backbone.utils.general_purpose import calculate_units_size, diff_pips

np.seterr(divide='ignore')

class HHLLBreakout(Strategy):
    pip_value = None
    minimum_lot = None
    maximum_lot = None
    contract_volume = None
    trade_tick_value_loss = None
    opt_params = None
    volume_step = None
    risk = None
    
    breakout_period = 20  # Parámetro configurable para el período de máximos/mínimos
    sma_period = 200  # Para filtro de tendencia opcional
    atr_multiplier = 2  # Para stop-loss dinámico

    def init(self):
        self.sma = self.I(ta.SMA, self.data.Close, timeperiod=self.sma_period)
        self.atr = self.I(ta.ATR, self.data.High, self.data.Low, self.data.Close)
        self.previous_hh = self.I(self.calc_previous_hh, self.data, self.breakout_period)
        self.previous_ll = self.I(self.calc_previous_ll, self.data, self.breakout_period)
        self.plot_hh = self.I(self.shift_and_plot, self.previous_hh, name="HH")  # Indicador desplazado para ploteo
        self.plot_ll = self.I(self.shift_and_plot, self.previous_ll, name="LL")  # Indicador desplazado para ploteo
    
    @staticmethod
    def calc_previous_hh(data, period):
        return np.array([data.High[max(0, i - period):i].max() if i >= period else np.nan for i in range(len(data))])

    @staticmethod
    def calc_previous_ll(data, period):
        return np.array([data.Low[max(0, i - period):i].min() if i >= period else np.nan for i in range(len(data))])

    @staticmethod
    def shift_and_plot(values):
        shifted = np.roll(values, -1)  # Desplaza una vela hacia atrás para el ploteo
        shifted[-1] = np.nan  # El último valor no tiene referencia futura
        return shifted
    
    def next(self):
        actual_date = self.data.index[-1]
        if self.opt_params and actual_date in self.opt_params.keys():
            for k, v in self.opt_params[actual_date].items():
                setattr(self, k, v)
        
        price = self.data.Close[-1]

        if self.position:
            if self.position.is_long and price < self.previous_ll[-1]:  # Salida si rompe el mínimo previo
                self.position.close()
            if self.position.is_short and price > self.previous_hh[-1]:  # Salida si rompe el máximo previo
                self.position.close()
        else:
            if price > self.previous_hh[-1] and price > self.sma[-1]:  # Compra si rompe HH previo y supera SMA200
                sl_price = price - self.atr_multiplier * self.atr[-1]
                self.open_trade('buy', price, sl_price)
            elif price < self.previous_ll[-1] and price < self.sma[-1]:  # Venta si rompe LL previo y está debajo de SMA200
                sl_price = price + self.atr_multiplier * self.atr[-1]
                self.open_trade('sell', price, sl_price)
    
    def open_trade(self, trade_type, price, sl_price):
        pip_distance = diff_pips(price, sl_price, pip_value=self.pip_value)
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
        if trade_type == 'buy':
            self.buy(size=units, sl=sl_price)
        else:
            self.sell(size=units, sl=sl_price)

