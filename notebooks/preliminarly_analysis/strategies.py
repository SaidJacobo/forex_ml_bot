
from backtesting import Strategy
import talib as ta
import pandas as pd

def ll_hh_indicator(close, window=None):
    if type(close) != pd.Series:
        close = close.s

    rolling_min = close.rolling(window=window, min_periods=1).min()
    is_lower_low = close == rolling_min

    rolling_max = close.rolling(window=window, min_periods=1).max()
    is_higher_high = close == rolling_max

    return is_lower_low, is_higher_high


def x_ll_hh_indicator(low, high, window=None):
    if type(low) != pd.Series:
        low = low.s

    if type(high) != pd.Series:
        high = high.s

    rolling_min = low.rolling(window=window, min_periods=1).min()
    is_lower_low = low == rolling_min

    rolling_max = high.rolling(window=window, min_periods=1).max()
    is_higher_high = high == rolling_max

    return is_lower_low, is_higher_high


class TradePullback(Strategy):
    pip_size = 0.0001
    risk=3
    rsi_threshold=99
    n_bars = 10
    
    def init(self):
        self.daily_sma_200 = self.I(
            ta.SMA, self.data.Close, timeperiod=200
        )

        self.daily_rsi_2 = self.I(
            ta.RSI, self.data.Close, 2
        )

        self.daily_ll, self.daily_hh = self.I(
            ll_hh_indicator, self.data.Close, window=self.n_bars
        )

    def next(self):
        actual_close = self.data.Close[-1]

        if self.position:
            first_trade = self.trades[0]

            first_trade_time = first_trade.entry_time
            today = self.data.index[-1]

            # Calcular el tiempo en la posición
            time_in_position = (today - first_trade_time).days

            if self.position.is_long:
                if self.daily_rsi_2 >= 65 or actual_close <= self.daily_sma_200 or time_in_position >= 5:
                    self.position.close()

            if self.position.is_short:
                if self.daily_rsi_2 <= 35 or time_in_position >= 5 or actual_close >= self.daily_sma_200:
                    self.position.close()

        else:
            actual_rsi = self.daily_rsi_2[-1]

            if actual_close > self.daily_sma_200 and actual_rsi <= 10 and self.daily_ll:
                self.buy(size=self.risk / 100)
                
            if actual_close < self.daily_sma_200 and actual_rsi >= 90 and self.daily_hh:
                self.sell(size=self.risk / 100)


class EndOfMonth(Strategy):
    risk=3
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
        actual_close = self.data.Close[-1]
        today = self.data.index[-1]

        if self.position:
            first_trade = self.trades[0]
            time_in_position = (today - first_trade.entry_time)
            time_in_position = time_in_position.days

            if self.position.is_long:
                if time_in_position > 5:
                    self.position.close()

        else:
            if today.day == self.day_to_buy:
                self.buy(size=self.risk/100)


class CumRSI(Strategy):
    pip_size = 0.0001
    risk=3
    rsi_threshold=99
    bars_low = 10

    def init(self):
        self.daily_sma_200 = self.I(
            ta.SMA, self.data.Close, timeperiod=200
        )

        self.daily_rsi_2 = self.I(
            ta.RSI, self.data.Close, 2
        )

    def next(self):
        actual_close = self.data.Close[-1]

        if self.position:
            first_trade = self.trades[0]

            first_trade_time = first_trade.entry_time
            if pd.api.types.is_datetime64_any_dtype(first_trade_time):
                if first_trade_time.tzinfo is None:
                    first_trade_time = first_trade_time

            today = self.data.index[-1]

            # Calcular el tiempo en la posición
            time_in_position = (today - first_trade_time).days

            if self.position.is_long:
                if self.daily_rsi_2 >= 65 or actual_close <= self.daily_sma_200 or time_in_position >= 5:
                    self.position.close()

            if self.position.is_short:
                if self.daily_rsi_2 <= 35 or actual_close >= self.daily_sma_200 or time_in_position >= 5 :
                    self.position.close()

        else:
            cum_rsi = self.daily_rsi_2[-1] + self.daily_rsi_2[-2]

            if actual_close > self.daily_sma_200 and cum_rsi <= 20:
                self.buy(size=self.risk / 100)
                
            if actual_close < self.daily_sma_200 and cum_rsi >= 80:
                self.sell(size=self.risk / 100)


class ExtremeTradePullback(Strategy):
    risk=1
    rsi_threshold=99
    bars_low = 10
    
    def init(self):
        self.daily_sma_200 = self.I(
            ta.SMA, self.data.Close, timeperiod=200
        )

        self.daily_rsi_2 = self.I(
            ta.RSI, self.data.Close, 2
        )

        self.daily_ll, self.daily_hh = self.I(
            ll_hh_indicator, self.data.Close, window=self.bars_low
        )

        self.last_day = None

    def next(self):
        actual_close = self.data.Close[-1]
        today = self.data.index[-1]

        if self.position:
            first_trade = self.trades[0]

            first_trade_time = first_trade.entry_time

            # Calcular el tiempo en la posición
            time_in_position = (today - first_trade_time).days

            if self.position.is_long:
                if time_in_position >= 5:
                    self.position.close()

            if self.position.is_short:
                if self.daily_rsi_2 <= 35 or time_in_position >= 5 or actual_close >= self.daily_sma_200:
                    self.position.close()

        elif not self.orders:
            actual_rsi = self.daily_rsi_2[-1]

            if actual_close > self.daily_sma_200 and actual_rsi <= 10 and self.daily_ll:
                self.buy(size=self.risk / 100, limit=actual_close * 0.90)
                self.buy(size=self.risk / 100, limit=actual_close * 0.95)
                self.buy(size=self.risk / 100, limit=actual_close * 0.97)

                self.last_day = today
                
            if actual_close < self.daily_sma_200 and actual_rsi >= 90 and self.daily_hh:
                self.sell(size=self.risk / 100, limit=actual_close * 1.1)
                self.sell(size=self.risk / 100, limit=actual_close * 1.05)
                self.sell(size=self.risk / 100, limit=actual_close * 1.07)
                self.last_day = today
        
        elif self.orders:
            time_order_pending = (today - self.last_day).days
            if time_order_pending > 5:
                for order in self.orders:
                    order.cancel()


