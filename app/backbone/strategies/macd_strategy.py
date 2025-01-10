from datetime import datetime, timedelta
import pytz
import talib as ta
from backbone.trader_bot import TraderBot
from backtesting import Strategy, Backtest
from backtesting.lib import crossover
import numpy as np
import MetaTrader5 as mt5
import numpy as np

from backbone.utils.general_purpose import calculate_units_size, diff_pips

np.seterr(divide='ignore')


def  optim_func(series):
    return (series['Return [%]'] /  (1 + (-1*series['Max. Drawdown [%]']))) * np.log(1 + series['# Trades'])

class Macd(Strategy):
    pip_value = None
    minimum_lot = None
    maximum_lot = None
    contract_volume = None
    trade_tick_value_loss = None
    opt_params = None
    volume_step = None
    risk=None
    
    sma_period = 200
    macd_fast_period = 7
    macd_slow_period = 26
    macd_signal_period = 9
    atr_multiplier = 1.5
    
    cum_rsi_open_threshold = 65
    cum_rsi_close_threshold = 45
    
    rsi_period = 2
    
    def init(self):
        self.sma = self.I(
            ta.SMA, self.data.Close, timeperiod=self.sma_period
        )

        self.macd, self.macdsignal, self.macdhist = self.I(
            ta.MACD, 
            self.data.Close, 
            fastperiod=self.macd_fast_period, 
            slowperiod=self.macd_slow_period, 
            signalperiod=self.macd_signal_period
        )
        
        self.atr = self.I(ta.ATR, self.data.High, self.data.Low, self.data.Close)
        
        self.rsi = self.I(ta.RSI, self.data.Close, timeperiod=self.rsi_period)

    def next(self):
        cum_rsi = self.rsi[-1] + self.rsi[-2]
        price = self.data.Close[-1]
    
        if self.position:
            if self.position.is_long:
                if cum_rsi > self.cum_rsi_close_threshold:
                    self.position.close()

            if self.position.is_short:
                if cum_rsi < 100-self.cum_rsi_close_threshold:
                    self.position.close()

        else:

            if crossover(self.macdsignal, self.macd) and cum_rsi <= 100-self.cum_rsi_open_threshold and price > self.sma[-1]:        
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
                
            if crossover(self.macd, self.macdsignal) and cum_rsi >= self.cum_rsi_open_threshold and price < self.sma[-1]:
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
        cum_rsi = self.rsi[-1] + self.rsi[-2]


        open_positions = trader.get_open_positions()

        if open_positions:
            if open_positions[-1].type == mt5.ORDER_TYPE_BUY:
                if cum_rsi > self.cum_rsi_close_threshold:
                    trader.close_order(open_positions[-1])

            if open_positions[-1].type == mt5.ORDER_TYPE_SELL:
                if cum_rsi < 100-self.cum_rsi_close_threshold:
                    trader.close_order(open_positions[-1])

        else:

            if crossover(self.macdsignal, self.macd) and cum_rsi <= 100-self.cum_rsi_open_threshold and actual_close > self.sma[-1]:
                info_tick = trader.get_info_tick()
                price = info_tick.ask
                
                capital_to_risk = trader.equity * self.risk / 100
                units = capital_to_risk / price
                
                lots = round(units / trader.contract_volume, 2)
                
                trader.open_order(
                    type_='buy',
                    price=price,
                    size=lots
                )  
                
            if crossover(self.macd, self.macdsignal) and cum_rsi >= self.cum_rsi_open_threshold and actual_close < self.sma[-1]:
                info_tick = trader.get_info_tick()
                price = info_tick.bid
                
                capital_to_risk = trader.equity * self.risk / 100
                units = capital_to_risk / price
                
                lots = round(units / trader.contract_volume, 2)
                
                trader.open_order(
                    type_='sell',
                    price=price,
                    size=lots
                )
                
