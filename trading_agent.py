import talib
import pandas as pd
import os


class TradingAgent():
  def __init__(self, start_money, trading_strategy, threshold_up, threshold_down):
    self.money = start_money
    self.open_position = False
    self.buy_history = {}
    self.sell_history = {}
    self.wallet_evolution = {}
    self.trading_strategy = trading_strategy
    self.threshold_up = threshold_up
    self.threshold_down = threshold_down

  def calculate_indicators(self, df):
    df['ema_15'] = talib.EMA(df['Close'], timeperiod=15)
    df['ema_30'] = talib.EMA(df['Close'], timeperiod=30)
    df['ema_60'] = talib.EMA(df['Close'], timeperiod=60)
    df['momentum_5'] = talib.MOM(df['Close'], timeperiod=5)
    df['rsi'] = talib.RSI(df['Close'])

    upper_band, middle_band, lower_band = talib.BBANDS(df['Close'], timeperiod=5)
    df['upper_bband'] = upper_band
    df['middle_bband'] = middle_band
    df['lower_bband'] = lower_band

    macd, macdsignal, macdhist = talib.MACD(df['Close'], fastperiod=12, slowperiod=26, signalperiod=9)
    df['macd'] = macd
    df['macdsignal'] = macdsignal
    df['macdhist'] = macdhist

    df['change_percent_1_day'] = (((df['Close']- df['Close'].shift(1)) / df['Close']) * 100).round(0)
    df['change_percent_2_day'] = (((df['Close']- df['Close'].shift(2)) / df['Close']) * 100).round(0)
    df['change_percent_3_day'] = (((df['Close']- df['Close'].shift(3)) / df['Close']) * 100).round(0)
    df['change_percent_4_day'] = (((df['Close']- df['Close'].shift(4)) / df['Close']) * 100).round(0)
    df['change_percent_5_day'] = (((df['Close']- df['Close'].shift(5)) / df['Close']) * 100).round(0)
    df['change_percent_6_day'] = (((df['Close']- df['Close'].shift(6)) / df['Close']) * 100).round(0)
    df['change_percent_7_day'] = (((df['Close']- df['Close'].shift(7)) / df['Close']) * 100).round(0)

    df = df.drop(columns=['Open','High','Low', 'Dividends', 'Stock Splits'])

    df = df.dropna()
    return df
  
  def buy(self, date, price):
    date = date.strftime('%Y-%m-%d')
    self.buy_history[date] = price
    self.open_position = True
    print('='*16, f'se abrio una nueva posicion el {date}', '='*16)

  def sell(self, date, price):
    date = date.strftime('%Y-%m-%d')
    self.sell_history[date] = price

    last_buy_date = max(list(self.buy_history.keys()))
    self.update_wallet(last_buy_date=last_buy_date, sell_date=date)
    self.open_position = False
    print('='*16, f'se cerro una posicion el {date}', '='*16)

  def update_wallet(self, last_buy_date, sell_date):
      self.money += self.sell_history[sell_date] - self.buy_history[last_buy_date]
      self.wallet_evolution[sell_date] = self.money
      print(f'money: {self.money}')

  def take_operation_decision(self, pred,  actual_market_data, actual_date):

    result = self.trading_strategy(
      pred, 
      actual_market_data, 
      self.open_position,
      self.threshold_up,
      self.threshold_down
    )

    print(f'result: {result}')

    if result == 'buy':
      price = actual_market_data.iloc[0].Close
      self.buy(actual_date, price)

    elif result == 'sell':
      price = actual_market_data.iloc[0].Close
      self.sell(actual_date, price)
    
    elif result == 'wait':
      pass
  
  def get_orders(self):
    print('saving results')

    df_buys = pd.DataFrame(
      {
        'date': self.buy_history.keys(),
        'buy':self.buy_history.values()
      }
    )

    df_sells = pd.DataFrame(
      {      
        'date': self.sell_history.keys(), 
        'sell':self.sell_history.values()
      }
    )

    df_wallet = pd.DataFrame(
      {      
        'date': self.wallet_evolution.keys(), 
        'wallet': self.wallet_evolution.values()
      }
    )

    return df_buys, df_sells, df_wallet