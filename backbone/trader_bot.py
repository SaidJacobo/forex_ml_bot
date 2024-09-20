from abc import ABC, abstractmethod
import pandas as pd
import MetaTrader5 as mt5
import telebot

time_frames = {
    'M1': mt5.TIMEFRAME_M1,
    'M2': mt5.TIMEFRAME_M2,
    'M3': mt5.TIMEFRAME_M3,
    'M4': mt5.TIMEFRAME_M4,
    'M5': mt5.TIMEFRAME_M5,
    'M10': mt5.TIMEFRAME_M10,
    'M12': mt5.TIMEFRAME_M12,
    'M15': mt5.TIMEFRAME_M15,
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

class TraderBot(ABC):
    
    def __init__(self, creds:dict):
        if not mt5.initialize():
            print("initialize() failed, error code =", mt5.last_error())
            quit()

        bot_token = creds['telegram_bot_token']
        chat_id = creds['telegram_chat_id']
        server = creds['server']
        account = creds['account']
        pw = creds['pw']

        self.mt5 = mt5

        self.bot = telebot.TeleBot(bot_token)
        self.chat_id = chat_id


        authorized = self.mt5.login(server=server, login=account, password=pw)

        if authorized:
            account_info_dict = self.mt5.account_info()._asdict()
            for prop in account_info_dict:
                print("  {}={}".format(prop, account_info_dict[prop]))
        else:
            print("failed to connect at account #{}, error code: {}".format(account, mt5.last_error()))
        

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


    @abstractmethod
    def calculate_indicators(self, df, drop_nulls=False):
        pass


    def get_open_positions(self, ticker):
        positions = self.mt5.positions_get(symbol=ticker)

        positions = [position for position in positions if position.comment == self.name]

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

        action = None
        action = self.mt5.TRADE_ACTION_PENDING if mt5_type in [self.mt5.ORDER_TYPE_BUY_LIMIT, self.mt5.ORDER_TYPE_SELL_LIMIT] else self.mt5.TRADE_ACTION_DEAL
        
        request = {
            "action": action,
            "symbol": ticker,
            "volume": lot,
            "type": mt5_type,
            "price": price,
            "magic": 234000,
            "comment": f'{self.name}',
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_FOK,
        }
        
        result = self.mt5.order_send(request)

        if result.retcode != self.mt5.TRADE_RETCODE_DONE:
            message = f"fallo al abrir orden en {self.name}, retcode={result.retcode}, comment {result.comment}"
            print(message)
            self.bot.send_message(chat_id=self.chat_id, text=message)

        else:
            message = f"Se abrio una nueva orden: {self.name}, lot: {lot}, price: {price}. Codigo: {result.retcode}"
            print(message)
            self.bot.send_message(chat_id=self.chat_id, text=message)

        
    def close_order(self, position):
        close_position_type = opposite_order_tpyes[position.type]

        if close_position_type == order_tpyes['buy'] or order_tpyes['buy_limit']:
            price = self.mt5.symbol_info_tick(position.symbol).ask

        else:
            price = self.mt5.symbol_info_tick(position.symbol).bid

        request={
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": close_position_type,
            "position": position.ticket,
            "price": price,
            "magic": 234000,
            "comment": f"{self.name} close",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_FOK,
        }

        result = self.mt5.order_send(request)

        if result.retcode != self.mt5.TRADE_RETCODE_DONE:
            message = f"fallo al cerrar orden en {self.name}, retcode: {result.retcode}"
            print(message)
            self.bot.send_message(chat_id=self.chat_id, text=message)

        else:
            message = f"Orden cerrada: {self.name} closed, {result}"
            print(message)
            self.bot.send_message(chat_id=self.chat_id, text=message)


    @abstractmethod
    def strategy(self, df, ticker, actual_date):
        pass

    @abstractmethod
    def run(self, tickers, timeframe, interval_minutes, noisy=False):
        pass
            
