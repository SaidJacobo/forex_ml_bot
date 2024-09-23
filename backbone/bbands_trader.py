from datetime import datetime, timedelta
import pytz
import talib
from backbone.trader_bot import TraderBot


class BbandsTrader(TraderBot):
    
    def __init__(self, ticker, lot_size, timeframe, creds):

        super().__init__(creds)

        self.ticker = ticker
        self.lot_size = lot_size
        self.timeframe = timeframe

        self.name = f'Bbands_{self.ticker}_{self.timeframe}'


    def calculate_indicators(self, df, drop_nulls=False, indicator_params:dict=None):
        upper_band, middle_band, lower_band = talib.BBANDS(df['Close'], timeperiod=indicator_params['bbands_timeperiod'])
        df['upper_bband'] = upper_band
        df['middle_bband'] = middle_band
        df['lower_bband'] = lower_band

        df['sma'] = talib.SMA(df['Close'], timeperiod=indicator_params['sma_timeperiod'])

        if drop_nulls:
            df = df.dropna()

        return df

    def strategy(self, df, actual_date, strategy_params:dict=None):
        open_positions = self.get_open_positions(self.ticker)
        open_orders = self.mt5.orders_get(symbol=self.ticker)

        close = df.iloc[-1].Close
        sma = df.iloc[-1].sma
        upper_bband = df.iloc[-1].upper_bband
        middle_bband = df.iloc[-1].middle_bband
        lower_bband = df.iloc[-1].lower_bband

        if open_positions:  # Si hay una posición abierta

            for position in open_positions:
                if position.type == self.mt5.ORDER_TYPE_BUY and close >= middle_bband:
                    self.close_order(position)
                
                elif position.type == self.mt5.ORDER_TYPE_SELL and close <= middle_bband:
                    self.close_order(position)

        elif not open_orders:

            if close > sma and close < lower_bband:
                info_tick = self.mt5.symbol_info_tick(self.ticker)
                price = info_tick.ask

                self.open_order(
                    ticker=self.ticker, 
                    lot=self.lot_size, 
                    type_='buy',
                    price=price
                )
            elif close < sma and close > upper_bband:
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


            
