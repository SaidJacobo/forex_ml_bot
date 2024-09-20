from datetime import datetime, timedelta
import time
import winsound
import pytz
import talib
from backbone.trader_bot import TraderBot

class EndOfMonthTrader(TraderBot):
    
    def __init__(self, ticker, lot_size, timeframe, creds):
        super().__init__(creds)

        self.ticker = ticker
        self.lot_size = lot_size
        self.timeframe = timeframe
        self.name = 'EndOfMonthTrader'


    def calculate_indicators(self, df, drop_nulls=False, indicator_params:dict=None):
        df['rsi'] = talib.RSI(df['Close'], timeperiod=indicator_params['rsi_time_period'])

        if drop_nulls:
            df = df.dropna()

        return df

    def strategy(self, df, actual_date, strategy_params:dict=None):
        open_positions = self.get_open_positions(self.ticker)
        open_orders = self.mt5.orders_get(symbol=self.ticker)

        if open_positions:  # Si hay una posición abierta
            rsi = df.iloc[-1].rsi
            
            for position in open_positions:
                if rsi >= strategy_params['rsi_threshold']:
                    self.close_order(position)

        elif not open_orders:
            actual_close = df.iloc[-1].Close
            yesterday_close = df.iloc[-2].Close

            actual_open = df.iloc[-1].Open
            yesterday_open = df.iloc[-2].Open

            two_days_bearish = actual_close < actual_open and yesterday_close < yesterday_open

            start_day = strategy_params['start_day']
            end_day = strategy_params['end_day']

            if actual_date.day >= start_day and actual_date.day <= end_day and two_days_bearish:  
                info_tick = self.mt5.symbol_info_tick(self.ticker)
                price = info_tick.ask

                self.open_order(
                    ticker=self.ticker, 
                    lot=self.lot_size, 
                    type_='buy',
                    price=price
                )

    def run(self, indicator_params:dict=None, strategy_params:dict=None):

        warm_up_bars = 500
        bars_to_trade = 10

        timezone = pytz.timezone("Etc/UTC")

        now = datetime.now(tz=timezone)
        
        print(f'excecuting run {self.name} at {now}')


        date_from = now - timedelta(days=bars_to_trade) - timedelta(days=warm_up_bars) 
        df = self.get_data(
            self.ticker,
            timeframe=self.timeframe, 
            date_from=date_from, 
            date_to=now,
        )

        df = self.calculate_indicators(df, indicator_params=indicator_params)
        
        self.strategy(df, ticker=self.ticker, actual_date=now, strategy_params=strategy_params)

    