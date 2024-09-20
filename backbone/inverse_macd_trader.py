from datetime import datetime, timedelta
import pytz
import talib
from backbone.trader_bot import TraderBot
from backtesting.lib import crossover

class InverseMacdTrader(TraderBot):
    
    def __init__(self, ticker, lot_size, timeframe, creds):

        super().__init__(creds)

        self.ticker = ticker
        self.lot_size = lot_size
        self.timeframe = timeframe

        self.name = f'InverseMacdTrader_{self.ticker}_{self.timeframe}'


    def calculate_indicators(self, df, drop_nulls=False, indicator_params:dict=None):
        macd_fast_period = indicator_params['macd_fast_period']
        macd_slow_period = indicator_params['macd_slow_period']
        macd_signal_period = indicator_params['macd_signal_period']
        rsi_period = indicator_params['rsi_period']
        sma_period = indicator_params['sma_period']
        df['macd'], df['macdsignal'], _ = talib.MACD(
            df['Close'], 
            fastperiod=macd_fast_period, 
            slowperiod=macd_slow_period, 
            signalperiod=macd_signal_period
        )

        df['sma'] = talib.SMA(df['Close'], timeperiod=sma_period)

        df['rsi'] = talib.RSI(df['Close'], timeperiod=rsi_period)

        if drop_nulls:
            df = df.dropna()

        return df

    def strategy(self, df, actual_date, strategy_params:dict=None):
        open_positions = self.get_open_positions(self.ticker)
        open_orders = self.mt5.orders_get(symbol=self.ticker)

        close = df.iloc[-1].Close
        sma = df.iloc[-1].sma
        macd = df.macd
        macdsignal = df.macdsignal
        rsi = df.iloc[-1].rsi
        previous_rsi = df.iloc[-2].rsi

        lower_threshold = strategy_params['rsi_lower_threshold']
        upper_threshold = strategy_params['rsi_upper_threshold']

        if open_positions:  # Si hay una posición abierta

            for position in open_positions:
                if position.type == self.mt5.ORDER_TYPE_BUY:
                    if crossover(self.macd, self.macdsignal):
                        self.close_order(position)
                
                elif position.type == self.mt5.ORDER_TYPE_SELL:
                    if crossover(self.macdsignal, self.macd):
                        self.close_order(position)

        elif not open_orders:

            cum_rsi = rsi + previous_rsi

            if crossover(macdsignal, macd) and cum_rsi < lower_threshold and close > sma:
                info_tick = self.mt5.symbol_info_tick(self.ticker)
                price = info_tick.ask

                self.open_order(
                    ticker=self.ticker, 
                    lot=self.lot_size, 
                    type_='buy',
                    price=price
                )
            elif crossover(macd, macdsignal) and cum_rsi > upper_threshold and close < sma:
                info_tick = self.mt5.symbol_info_tick(self.ticker)
                price = info_tick.bid

                self.open_order(
                    ticker=self.ticker, 
                    lot=self.lot_size, 
                    type_='sell',
                    price=price
                )

    def run(self, indicator_params:dict=None, strategy_params:dict=None):

        warm_up_bars = 500
        bars_to_trade = 10

        timezone = pytz.timezone("Etc/UTC")

        now = datetime.now(tz=timezone)

        print(f'excecuting run {self.name} on {self.ticker} {self.timeframe} at {now}')
        
        date_from = now - timedelta(days=bars_to_trade) - timedelta(days=warm_up_bars) 

        df = self.get_data(
            self.ticker,
            timeframe=self.timeframe, 
            date_from=date_from, 
            date_to=now,
        )

        df.index = df.index.tz_localize('UTC').tz_convert('UTC')
        
        df = self.calculate_indicators(df, drop_nulls=True, indicator_params=indicator_params)
        
        self.strategy(df, actual_date=now, strategy_params=strategy_params)


            
