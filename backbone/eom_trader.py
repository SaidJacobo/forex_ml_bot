from datetime import datetime, timedelta
import time
import winsound
import pytz
import talib
from backbone.trader_bot import TraderBot



class EndOfMonthTrader(TraderBot):
    
    def __init__(self, lot_size, day_of_month, days_to_hold, server, account, pw, telegram_bot_token, telegram_chat_id):
        super().__init__(server, account, pw, telegram_bot_token, telegram_chat_id)

        self.lot_size = lot_size
        self.day_of_month = day_of_month
        self.days_to_hold = days_to_hold
        self.name = 'EndOfMonthTrader'


    def calculate_indicators(self, df, drop_nulls=False):
        df['rsi'] = talib.RSI(df['Close'], timeperiod=2)
        df['sma_200'] = talib.SMA(df['Close'], timeperiod=200)

        if drop_nulls:
            df = df.dropna()

        return df

    def strategy(self, df, ticker, actual_date):

        open_positions = self.get_open_positions(ticker)
        open_orders = self.mt5.orders_get(symbol=ticker)


        if open_positions:  # Si hay una posición abierta

            for position in open_positions:

                position_date = datetime.fromtimestamp(position.time, tz=pytz.timezone("Etc/UTC"))

                time_in_position = (actual_date - position_date).days

                if time_in_position >= self.days_to_hold:
                    self.close_order(position)

        elif not open_orders and actual_date.day == self.day_of_month:  

            info_tick = self.mt5.symbol_info_tick(ticker)
            price = info_tick.ask

            self.open_order(
                ticker=ticker, 
                lot=self.lot_size, 
                type_='buy',
                price=price
            )

    def run(self, tickers, timeframe, noisy=False):

        warm_up_bars = 500
        bars_to_trade = 10

        timezone = pytz.timezone("Etc/UTC")

        now = datetime.now(tz=timezone)

        for ticker in tickers:

            date_from = now - timedelta(days=bars_to_trade) - timedelta(days=warm_up_bars) 
            df = self.get_data(
                ticker,
                timeframe=timeframe, 
                date_from=date_from, 
                date_to=now,
            )

            df = self.calculate_indicators(df)
            
            self.strategy(df, ticker=ticker, actual_date=now)

        if noisy:
            winsound.Beep(2000, 250)
            
