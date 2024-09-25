from datetime import datetime, timedelta
import pytz
import talib as ta
from backbone.trader_bot import TraderBot
from backtesting import Strategy, Backtest
from backtesting.lib import crossover
import numpy as np
import MetaTrader5 as mt5

def  optim_func(series):
    return (series['Return [%]'] /  (1 + (-1*series['Max. Drawdown [%]']))) * np.log(1 + series['# Trades'])

class Macd(Strategy):
    risk=3
    sma_period = 200
    
    macd_fast_period = 7
    macd_slow_period = 26
    macd_signal_period = 9
    
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
        
        self.rsi = self.I(ta.RSI, self.data.Close, timeperiod=self.rsi_period)

    def next(self):
        actual_close = self.data.Close[-1]
        cum_rsi = self.rsi[-1] + self.rsi[-2]

        if self.position:
            if self.position.is_long:
                if cum_rsi > self.cum_rsi_close_threshold:
                    self.position.close()

            if self.position.is_short:
                if cum_rsi < 100-self.cum_rsi_close_threshold:
                    self.position.close()

        else:

            if crossover(self.macdsignal, self.macd) and cum_rsi <= 100-self.cum_rsi_open_threshold and actual_close > self.sma:
                self.buy(size=self.risk / 100)
                
            if crossover(self.macd, self.macdsignal) and cum_rsi >= self.cum_rsi_open_threshold and actual_close < self.sma:
                self.sell(size=self.risk / 100)
                
                
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

            if crossover(self.macdsignal, self.macd) and cum_rsi <= 100-self.cum_rsi_open_threshold and actual_close > self.sma:
                info_tick = trader.get_info_tick()
                price = info_tick.ask
                
                trader.open_order(
                    ticker=self.ticker, 
                    lot=self.lot_size, 
                    type_='buy',
                    price=price
                )  
                
            if crossover(self.macd, self.macdsignal) and cum_rsi >= self.cum_rsi_open_threshold and actual_close < self.sma:
                info_tick = trader.get_info_tick()
                price = info_tick.bid
                
                trader.open_order(
                    ticker=self.ticker, 
                    lot=self.lot_size, 
                    type_='sell',
                    price=price
                )
                
class MacdTrader:
    
    def __init__(self, ticker, timeframe, creds, opt_params, wfo_params):
        
        name = f'Macd_{ticker}_{timeframe}'
        
        self.trader = TraderBot(
            name=name,
            ticker=ticker, 
            timeframe=timeframe, 
            creds=creds
        )
        
        self.opt_params = opt_params
        self.wfo_params = wfo_params
        self.opt_params['maximize'] = optim_func
    
    def run(self):
            warmup_bars = self.wfo_params['warmup_bars']
            look_back_bars = self.wfo_params['look_back_bars']

            timezone = pytz.timezone("Etc/UTC")
            now = datetime.now(tz=timezone)
            date_from = now - timedelta(hours=look_back_bars) - timedelta(hours=warmup_bars) 
            
            print(f'excecuting run {self.trader.name} at {now}')
            
            df = self.trader.get_data(
                date_from=date_from, 
                date_to=now,
            )

            df.index = df.index.tz_localize('UTC').tz_convert('UTC')

            bt_train = Backtest(
                df, 
                Macd,
                commission=7e-4,
                cash=15_000, 
                margin=1/30
            )
            
            stats_training = bt_train.optimize(
                **self.opt_params
            )
            
            bt = Backtest(
                df, 
                Macd,
                commission=7e-4,
                cash=15_000, 
                margin=1/30
            )
            
            opt_params = {param: getattr(stats_training._strategy, param) for param in self.opt_params.keys() if param != 'maximize'}

            stats = bt.run(
                **opt_params
            )

            bt_train._results._strategy.next_live(trader=self.trader)   

