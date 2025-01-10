from datetime import datetime, timedelta
import pytz
import talib as ta
from backbone.trader_bot import TraderBot
from backtesting import Strategy, Backtest
import numpy as np
import MetaTrader5 as mt5
import numpy as np

np.seterr(divide='ignore')


class EndOfMonth(Strategy):
    risk=None
    n=10
    day_to_buy = 25
    
    def init(self):
        self.daily_sma_200 = self.I(
            ta.SMA, self.data.Close, timeperiod=200
        )

        self.rsi_2 = self.I(
            ta.RSI, self.data.Close, 2
        )
        
    def next(self):
        today = self.data.index[-1]

        if self.position:
            first_trade = self.trades[0]
            time_in_position = (today - first_trade.entry_time)
            time_in_position = time_in_position.days

            if self.position.is_long:
                if self.rsi_2 > 90:
                    self.position.close()

        else:
            today_bearish = self.data.Close[-1] < self.data.Open[-1]
            yesterday_bearish = self.data.Close[-2] < self.data.Open[-2
                                                                 ]
            if today.day >= 25 and today.day <= 31 and today_bearish and yesterday_bearish:
                
                capital_to_risk = self.equity * self.risk / 100
                units = int(capital_to_risk / self.data.Close[-1])
                
                self.buy(size=units)
                
    def next_live(self, trader:TraderBot):
        today = self.data.index[-1]
        open_positions = trader.get_open_positions()

        if open_positions:
            if open_positions[-1].type == mt5.ORDER_TYPE_BUY:
                if self.rsi_2 > 90:
                    trader.close_order(open_positions[-1])

        else:
            today_bearish = self.data.Close[-1] < self.data.Open[-1]
            yesterday_bearish = self.data.Close[-2] < self.data.Open[-2]
            if today.day >= 25 and today.day <= 31 and today_bearish and yesterday_bearish:
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

class EndOfMonthTrader(TraderBot):
    
    def __init__(self, ticker, timeframe, contract_volume, creds, opt_params, wfo_params):
        name = f'EOM_{ticker}_{timeframe}'
        
        self.trader = TraderBot(
            name=name,
            ticker=ticker, 
            timeframe=timeframe, 
            creds=creds,
            contract_volume=contract_volume
        )
        
        self.strategy = EndOfMonth

    def run(self):

            timezone = pytz.timezone("Etc/UTC")
            now = datetime.now(tz=timezone)
            date_from = now - timedelta(days=30) 
            
            print(f'excecuting run {self.trader.name} at {now}')
            
            df = self.trader.get_data(
                date_from=date_from, 
                date_to=now,
            )

            df.index = df.index.tz_localize('UTC').tz_convert('UTC')

            bt = Backtest(
                df, 
                self.strategy,
                commission=7e-4,
                cash=15_000, 
                margin=1/30
            )

            stats = bt.run()

            bt._results._strategy.next_live(trader=self.trader)   

