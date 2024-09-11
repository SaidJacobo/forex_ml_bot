import pandas as pd
import MetaTrader5 as mt5
import talib


time_frames = {
    'M1': mt5.TIMEFRAME_M1,
    'M2': mt5.TIMEFRAME_M2,
    'M3': mt5.TIMEFRAME_M3,
    'M4': mt5.TIMEFRAME_M4,
    'M5': mt5.TIMEFRAME_M5,
    'M10': mt5.TIMEFRAME_M10,
    'M12': mt5.TIMEFRAME_M12,
    'M20': mt5.TIMEFRAME_M20,
    'M30': mt5.TIMEFRAME_M30,
    'H1': mt5.TIMEFRAME_H1,
    'H2': mt5.TIMEFRAME_H2,
    'H3': mt5.TIMEFRAME_H3,
    'H4': mt5.TIMEFRAME_H4,
    'H6': mt5.TIMEFRAME_H6,
    'H8': mt5.TIMEFRAME_H8,
    'H12': mt5.TIMEFRAME_H12,
    'D1': mt5.TIMEFRAME_D1,
    'W1': mt5.TIMEFRAME_W1,
    'MN1': mt5.TIMEFRAME_MN1,
}

order_tpyes = {
    'buy': mt5.ORDER_TYPE_BUY,
    'sell': mt5.ORDER_TYPE_SELL,
    'buy_limit': mt5.ORDER_TYPE_BUY_LIMIT,
    'sell_limit': mt5.ORDER_TYPE_SELL_LIMIT,
}

opposite_order_tpyes = {
    mt5.ORDER_TYPE_BUY: mt5.ORDER_TYPE_SELL,
    mt5.ORDER_TYPE_SELL: mt5.ORDER_TYPE_BUY,
}

class RealtimeTrader():
    
    def __init__(self):
        if not mt5.initialize():
            print("initialize() failed, error code =", mt5.last_error())
            quit()

        self.mt5 = mt5

    def get_data(self, ticker, timeframe, date_from, date_to):
        rates = self.mt5.copy_rates_range(ticker, time_frames[timeframe], date_from, date_to)
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')

        df = df.rename(columns={
            'time': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'tick_volume': 'Volume'
        }).set_index('Date')

        return df


    def calculate_indicators(self, df, drop_nulls=False):
        df['rsi'] = talib.RSI(df['Close'], timeperiod=2)
        df['sma_200'] = talib.SMA(df['Close'], timeperiod=200)

        if drop_nulls:
            df = df.dropna()

        return df


    def get_open_positions(self, ticker):
        positions = self.mt5.positions_get(symbol=ticker)

        return positions


    def open_order(self, ticker, type_, lot, price=None):
        symbol_info = mt5.symbol_info(ticker)
        if symbol_info is None:
            print(ticker, "not found, can not call order_check()")
            
        
        # if the symbol is unavailable in MarketWatch, add it
        if not symbol_info.visible:
            print(ticker, "is not visible, trying to switch on")
            if not self.mt5.symbol_select(ticker, True):
                print("symbol_select({}}) failed, exit", ticker)
 
        mt5_type = order_tpyes[type_]
        
        info_tick = self.mt5.symbol_info_tick(ticker)

        if not price:
            price = info_tick.ask if mt5_type in [self.mt5.ORDER_TYPE_BUY, self.mt5.ORDER_TYPE_BUY_LIMIT] else info_tick.bid

        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": ticker,
            "volume": lot,
            "type": mt5_type,
            "price": price,
            "magic": 234000,
            "comment": "python script open",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_FOK,
        }
        
        result = self.mt5.order_send(request)
        print("1. order_send(): by {} {} lots at {}".format(ticker, lot, price));

        if result.retcode != self.mt5.TRADE_RETCODE_DONE:
            print("2. order_send failed, retcode={}, comment {}".format(result.retcode, result.comment))

        else:
            print("2. order_send done, ", result.retcode)

        

    def close_order(self, open_positions):

        for position in open_positions:

            close_position_type = opposite_order_tpyes[position.type]

            if close_position_type == order_tpyes['buy'] or order_tpyes['buy_limit']:
                price = self.mt5.symbol_info_tick(position.symbol).ask

            else:
                price = self.mt5.symbol_info_tick(position.symbol).bid


            price = self.mt5.symbol_info_tick(position.symbol).bid

            deviation=20
            
            request={
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": close_position_type,
                "position": position.ticket,
                "price": price,
                "deviation": deviation,
                "magic": 234000,
                "comment": "python script close",
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self.mt5.ORDER_FILLING_FOK,
            }
            # send a trading request
            result = self.mt5.order_send(request)
            # check the execution result
            print("3. close position #{}: sell {} {} lots at {} with deviation={} points".format(position.ticket,position.symbol,position.volume, price, deviation))
            if result.retcode != self.mt5.TRADE_RETCODE_DONE:
                print("4. order_send failed, retcode={}".format(result.retcode))
                print("   result",result)
            else:
                print("4. position #{} closed, {}".format(position.ticket,result))
                # request the result as a dictionary and display it element by element
                result_dict=result._asdict()
                for field in result_dict.keys():
                    print("   {}={}".format(field,result_dict[field]))
                    # if this is a trading request structure, display it element by element as well
                    if field=="request":
                        traderequest_dict=result_dict[field]._asdict()
                        for tradereq_filed in traderequest_dict:
                            print("       traderequest: {}={}".format(tradereq_filed,traderequest_dict[tradereq_filed]))



    def modify_order(self):
        pass
