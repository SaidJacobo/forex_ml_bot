from datetime import datetime, timedelta
from backtesting import Strategy, Backtest
import pytz
import talib as ta
from backbone.trader_bot import TraderBot
import MetaTrader5 as mt5
import numpy as np
import numpy as np

np.seterr(divide='ignore')


def  optim_func(series):
    return (series['Return [%]'] /  (1 + (-1*series['Max. Drawdown [%]']))) * np.log(1 + series['# Trades'])

class MeanReversion(Strategy):
    sma_period = 50
    deviation_threshold = 0.01
    risk = 1
    cum_rsi_up_threshold = 75
    cum_rsi_down_threshold = 25
    
    def init(self):
        # Calcular la media móvil simple (SMA)
        self.sma = self.I(ta.SMA, self.data.Close, timeperiod=self.sma_period)
        self.rsi = self.I(ta.RSI, self.data.Close, timeperiod=2)

    def next(self):
        # Precio actual y valor de la SMA
        actual_close = self.data.Close[-1]
        sma_value = self.sma[-1]
        cum_rsi = self.rsi[-1] + self.rsi[-2]

        # Desviación del precio con respecto a la SMA (en porcentaje)
        deviation = (actual_close - sma_value) / sma_value

        if self.position:
            if self.position.is_long and actual_close >= self.sma:
                self.position.close()

            if self.position.is_short and actual_close <= self.sma:
                self.position.close()  
        
        else:
            # Condiciones para comprar (precio por debajo de la SMA más del umbral de desviación)
            if deviation <= -self.deviation_threshold and cum_rsi <= self.cum_rsi_down_threshold:

                capital_to_risk = self.equity * self.risk / 100
                units = int(capital_to_risk / actual_close)
                
                self.buy(size=units)

            # Condiciones para vender (precio por encima de la SMA más del umbral de desviación)
            elif deviation >= self.deviation_threshold and cum_rsi >= self.cum_rsi_up_threshold:
                
                capital_to_risk = self.equity * self.risk / 100
                units = int(capital_to_risk / actual_close)
                
                self.sell(size=units)
    
    def next_live(self, trader:TraderBot):
        actual_close = self.data.Close[-1]
        sma_value = self.sma[-1]
        cum_rsi = self.rsi[-1] + self.rsi[-2]

        # Desviación del precio con respecto a la SMA (en porcentaje)
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
                
                capital_to_risk = trader.equity * self.risk / 100
                units = capital_to_risk / price
                
                lots = round(units / trader.contract_volume, 2)
                
                trader.open_order(
                    lot=self.lot_size, 
                    type_='buy',
                    price=price,
                    size=lots
                )

            # Condiciones para vender (precio por encima de la SMA más del umbral de desviación)
            elif deviation >= self.deviation_threshold and cum_rsi >= self.cum_rsi_up_threshold:
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

class MeanRevTrader():
    
    def __init__(self, ticker, timeframe, contract_volume, creds, opt_params, wfo_params):
        name = f'MeanRevTrader_{ticker}_{timeframe}'
        
        self.trader = TraderBot(
            name=name,
            ticker=ticker, 
            timeframe=timeframe, 
            creds=creds,
            contract_volume=contract_volume
        )
        
        self.opt_params = opt_params
        self.wfo_params = wfo_params
        self.opt_params['maximize'] = optim_func
        self.strategy = MeanReversion

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
            self.strategy,
            commission=7e-4,
            cash=15_000, 
            margin=1/30
        )
        
        stats_training = bt_train.optimize(
            **self.opt_params
        )
        
        bt = Backtest(
            df, 
            self.strategy,
            commission=7e-4,
            cash=15_000, 
            margin=1/30
        )
        
        opt_params = {param: getattr(stats_training._strategy, param) for param in self.opt_params.keys() if param != 'maximize'}

        stats = bt.run(
            **opt_params
        )

        bt_train._results._strategy.next_live(trader=self.trader)         
