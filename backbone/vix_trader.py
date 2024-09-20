from datetime import datetime, timedelta
import winsound
import pandas as pd
import pytz
import talib
from backbone.trader_bot import TraderBot
import yfinance as yf


class VixTrader(TraderBot):
    
    def __init__(self, ticker, lot_size, timeframe, creds):
        super().__init__(creds)

        self.ticker = ticker
        self.lot_size = lot_size
        self.timeframe = timeframe
        self.name = f'VixTrader_{self.ticker}_{self.timeframe}'

    def _ll_hh_indicator(self, close, window=None):
        if type(close) != pd.Series:
            close = close.s

        rolling_min = close.rolling(window=window, min_periods=1).min()
        is_lower_low = close == rolling_min

        rolling_max = close.rolling(window=window, min_periods=1).max()
        is_higher_high = close == rolling_max

        return is_lower_low, is_higher_high

    def calculate_indicators(self, df, drop_nulls=False, indicator_params:dict=None):
        df['rsi'] = talib.RSI(df['Close'], timeperiod=indicator_params['rsi_timeperiod'])
        df['cumrsi'] = df['rsi'].rolling(window=indicator_params['cum_rsi_window']).sum()
        df['sma'] = talib.SMA(df['Close'], timeperiod=indicator_params['sma_timeperiod'])
        df['vix_sma'] = talib.SMA(df['VixClose'], timeperiod=indicator_params['vix_sma_timeperiod'])
        df['lower_low'], df['higher_high'] = self._ll_hh_indicator(df.Close, window=indicator_params['llow_hhigh_window'])

        if drop_nulls:
            df = df.dropna()

        return df

    def strategy(self, df, actual_date, strategy_params:dict=None):

        open_positions = self.get_open_positions(self.ticker)
        open_orders = self.mt5.orders_get(symbol=self.ticker)

        close = df.iloc[-1].Close
        sma = df.iloc[-1].sma
        vix_close = df.iloc[-1].VixClose
        vix_sma = df.iloc[-1].vix_sma
        higher_high = df.iloc[-1].higher_high
        cumrsi = df.iloc[-1].cumrsi
        vix_above_sma = vix_close > (vix_sma * (1 + strategy_params['percent_above_sma']))

        if open_positions:  # Si hay una posición abierta

            for position in open_positions:
                if higher_high:
                    self.close_order(position)

        elif not open_orders:

            if vix_above_sma and cumrsi <= strategy_params['cum_rsi_threshold'] and close > sma:
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

        print(f'excecuting run {self.name} on {self.ticker} {self.timeframe} at {now}')
        
        date_from = now - timedelta(days=bars_to_trade) - timedelta(days=warm_up_bars) 
        
        vix = yf.Ticker("^VIX").history(interval='1h')
        vix.rename(
            columns={'Close':'VixClose'}, inplace=True
        )

        vix.index = vix.index.tz_convert('UTC')


        df = self.get_data(
            self.ticker,
            timeframe=self.timeframe, 
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

        full_df = self.calculate_indicators(
            full_df, 
            drop_nulls=True, 
            indicator_params=indicator_params
        )
        
        self.strategy(full_df, actual_date=now, strategy_params=strategy_params)

            
