from datetime import datetime, timedelta
import time
import winsound
import pandas as pd
import pytz
import talib
from backbone.trader_bot import TraderBot
import yfinance as yf


class VixTrader(TraderBot):
    
    def __init__(self, lot_size, llow_hhigh_window, server, account, pw, telegram_bot_token, telegram_chat_id):
        super().__init__(server, account, pw, telegram_bot_token, telegram_chat_id)

        self.lot_size = lot_size
        self.llow_hhigh_window = llow_hhigh_window
        self.name = 'VixTrader'


    def calculate_indicators(self, df, drop_nulls=False):
        df['rsi'] = talib.RSI(df['Close'], timeperiod=2)
        df['cumrsi'] = df['rsi'].rolling(window=2).sum()
        df['sma_200'] = talib.SMA(df['Close'], timeperiod=200)
        df['vix_sma_10'] = talib.SMA(df['VixClose'], timeperiod=10)
        df['lower_low'], df['higher_high'] = self._ll_hh_indicator(df.Close, window=self.llow_hhigh_window)

        if drop_nulls:
            df = df.dropna()

        return df

    def strategy(self, df, ticker, actual_date):

        open_positions = self.get_open_positions(ticker)
        open_orders = self.mt5.orders_get(symbol=ticker)

        close = df.iloc[-1].Close
        sma_200 = df.iloc[-1].sma_200
        vix_close = df.iloc[-1].VixClose
        vix_sma_10 = df.iloc[-1].vix_sma_10
        higher_high = df.iloc[-1].higher_high
        cumrsi = df.iloc[-1].cumrsi
        vix_above_sma = vix_close > (vix_sma_10 * (1 + 0.05))

        if open_positions:  # Si hay una posición abierta

            for position in open_positions:
                if higher_high:
                    self.close_order(position)

        elif not open_orders:

            if vix_above_sma and cumrsi <= 50 and close > sma_200:
                info_tick = self.mt5.symbol_info_tick(ticker)
                price = info_tick.ask

                self.open_order(
                    ticker=ticker, 
                    lot=self.lot_size, 
                    type_='buy',
                    price=price
                )

    def _ll_hh_indicator(self, close, window=None):
        if type(close) != pd.Series:
            close = close.s

        rolling_min = close.rolling(window=window, min_periods=1).min()
        is_lower_low = close == rolling_min

        rolling_max = close.rolling(window=window, min_periods=1).max()
        is_higher_high = close == rolling_max

        return is_lower_low, is_higher_high

    def run(self, tickers, timeframe, noisy=False):

        warm_up_bars = 500
        bars_to_trade = 10

        timezone = pytz.timezone("Etc/UTC")

        now = datetime.now(tz=timezone)

        print(f'excecuting run {self.name} at {now}')
        
        date_from = now - timedelta(days=bars_to_trade) - timedelta(days=warm_up_bars) 
        
        vix = yf.Ticker("^VIX").history(interval='1h')
        vix.rename(
            columns={'Close':'VixClose'}, inplace=True
        )
        vix.index = vix.index.tz_convert('UTC')


        for ticker in tickers:
            df = self.get_data(
                ticker,
                timeframe=timeframe, 
                date_from=date_from, 
                date_to=now,
            )

            df.index = df.index.tz_localize('UTC').tz_convert('UTC')

            full_df = pd.merge(
                df, 
                vix[['VixClose']], 
                left_index=True, 
                right_index=True
            )


            full_df = self.calculate_indicators(full_df, drop_nulls=True)
            
            self.strategy(full_df, ticker=ticker, actual_date=now)

        if noisy:
            winsound.Beep(2000, 250)

            
