import talib
import pandas as pd
import numpy as np

class TradingAgent():
  def __init__(self, tickers, start_money, trading_strategy, threshold_up, threshold_down, allowed_days_in_position):
    self.tickers = tickers
    self.money = start_money
    self.allowed_days_in_position = allowed_days_in_position
    self.wallet_evolution = {}
    self.trading_strategy = trading_strategy
    self.threshold_up = threshold_up
    self.threshold_down = threshold_down
    
    self.buy_history = {}
    self.sell_history = {}
    self.position_manager = {}
    
    for ticker in self.tickers:
      self.position_manager[ticker] = {}
      self.position_manager[ticker]['days_in_position'] = -1
      self.buy_history[ticker] = {}
      self.sell_history[ticker] = {}

  def calculate_indicators(self, df):
    df['ema_12'] = talib.EMA(df['Close'], timeperiod=12)
    df['ema_26'] = talib.EMA(df['Close'], timeperiod=26)
    df['ema_50'] = talib.EMA(df['Close'], timeperiod=50)
    df['ema_200'] = talib.EMA(df['Close'], timeperiod=200)
    df['rsi'] = talib.RSI(df['Close'])

    upper_band, middle_band, lower_band = talib.BBANDS(df['Close'], timeperiod=5)
    df['upper_bband'] = upper_band
    df['middle_bband'] = middle_band
    df['lower_bband'] = lower_band

    macd, macdsignal, macdhist = talib.MACD(df['Close'], fastperiod=12, slowperiod=26, signalperiod=9)
    df['macd'] = macd
    df['macdsignal'] = macdsignal
    df['macdhist'] = macdhist
    df['macdhist_yesterday'] = df['macdhist'].shift(1)

    df['macd_flag'] = 0
    df['macd_flag'] = np.where((df['macdhist_yesterday'] < 0) & (df['macdhist'] > 0), 1, df['macd_flag'])
    df['macd_flag'] = np.where((df['macdhist_yesterday'] > 0) & (df['macdhist'] < 0), -1, df['macd_flag'])

    df['change_percent_1_day'] = (((df['Close'] - df['Close'].shift(1)) / df['Close']) * 100).round(0)
    df['change_percent_2_day'] = (((df['Close'] - df['Close'].shift(2)) / df['Close']) * 100).round(0)
    df['change_percent_3_day'] = (((df['Close'] - df['Close'].shift(3)) / df['Close']) * 100).round(0)
    df['change_percent_4_day'] = (((df['Close'] - df['Close'].shift(4)) / df['Close']) * 100).round(0)
    df['change_percent_5_day'] = (((df['Close'] - df['Close'].shift(5)) / df['Close']) * 100).round(0)
    df['change_percent_6_day'] = (((df['Close'] - df['Close'].shift(6)) / df['Close']) * 100).round(0)
    df['change_percent_7_day'] = (((df['Close'] - df['Close'].shift(7)) / df['Close']) * 100).round(0)

    df = df.drop(columns=['Open','High','Low', 'Dividends', 'Stock Splits'])

    df = df.dropna()

    return df
  
  def buy(self, ticker, date, price):
    date = date.strftime('%Y-%m-%d')
    self.buy_history[ticker][date] = price
    print('='*16, f'se abrio una nueva posicion el {date}', '='*16)

  def sell(self, ticker, date, price):
    date = date.strftime('%Y-%m-%d')

    self.sell_history[ticker][date] = price

    last_buy_date = max(list(self.buy_history[ticker].keys()))
    self.update_wallet(ticker=ticker, last_buy_date=last_buy_date, sell_date=date)
    print('='*16, f'se cerro una posicion el {date}', '='*16)

  def update_wallet(self, ticker, last_buy_date, sell_date):
      self.money += self.sell_history[ticker][sell_date] - self.buy_history[ticker][last_buy_date]
      self.wallet_evolution[sell_date] = self.money
      print(f'money: {self.money}')

  def take_operation_decision(self, actual_market_data, actual_date):
    ticker = actual_market_data['ticker']
    result = self.trading_strategy(
      actual_market_data, 
      self.position_manager[ticker]['days_in_position'],
      self.allowed_days_in_position,
      self.threshold_up,
      self.threshold_down
    )

    print(f'result {ticker}: {result}')

    if result == 'buy':
      price = actual_market_data['Close']
      self.buy(ticker, actual_date, price)
      self.position_manager[ticker]['days_in_position'] = 0

    elif result == 'sell':
      price = actual_market_data.Close
      self.sell(ticker, actual_date, price)
      self.position_manager[ticker]['days_in_position'] = -1
    
    elif result == 'wait':
      if self.position_manager[ticker]['days_in_position'] > -1:
        self.position_manager[ticker]['days_in_position'] += 1
  

  def get_orders(self):
    print('saving results')

    df_buys = pd.DataFrame(self.buy_history)

    df_sells = pd.DataFrame(self.sell_history)
    
    df_buys = df_buys.reset_index().rename(columns={'index':'fecha'})
    df_sells = df_sells.reset_index().rename(columns={'index':'fecha'})

    df_wallet = pd.DataFrame(
      {      
        'date': self.wallet_evolution.keys(), 
        'wallet': self.wallet_evolution.values()
      }
    )

    return df_buys, df_sells, df_wallet