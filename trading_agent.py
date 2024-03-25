import talib
import pandas as pd
import numpy as np
from order import Order
from pandas import DataFrame

class TradingAgent():
  """Agente de Trading para tomar decisiones de compra y venta."""

  def __init__(self, 
               start_money:float, 
               trading_strategy, 
               threshold_up:int, 
               threshold_down:int, 
               allowed_days_in_position:int):
    """
    Inicializa el Agente de Trading.
    Args:
        start_money (float): Dinero inicial para realizar las operaciones.
        trading_strategy: Estrategia de trading.
        threshold_up (int): Umbral superior.
        threshold_down (int): Umbral inferior.
        allowed_days_in_position (int): Días permitidos en una posición.
    """
    self.money = start_money
    self.allowed_days_in_position = allowed_days_in_position
    self.wallet_evolution = {}
    self.trading_strategy = trading_strategy
    self.threshold_up = threshold_up
    self.threshold_down = threshold_down

    self.orders = []    

  def calculate_indicators(self, df:DataFrame):
    """Calcula indicadores técnicos para el DataFrame dado.

    Args:
        df (DataFrame): DataFrame de datos financieros.

    Returns:
        DataFrame: DataFrame con los indicadores calculados.
    """
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
  
  def open_position(self, type, ticker, date, price):
    order = Order(
      order_type=type, 
      ticker=ticker, 
      open_date=date, 
      open_price=price
    )
    """Abre una nueva posición de trading.

    Args:
        type: Tipo de operación (compra/venta).
        ticker (str): Ticker financiero.
        date (datetime): Fecha de la operación.
        price (float): Precio de la operación.
    """
    self.orders.append(order)

    print('='*16, f'se abrio una nueva posicion el {date}', '='*16)

  def close_position(self, order:Order, date, price):
    """Cierra una posición de trading.

    Args:
        order (Order): Orden de trading.
        date (datetime): Fecha de cierre de la operación.
        price (float): Precio de cierre de la operación.
    """
    order.close(close_price=price, close_date=date)
    self.__update_wallet(order)

    print('='*16, f'se cerro una posicion el {date}', '='*16)

  def __update_wallet(self, order:Order):
      """Actualiza el estado de la cartera después de cerrar una posición.

      Args:
          order (Order): Orden de trading.
      """
      self.money += order.profit
      self.wallet_evolution[order.close_date] = self.money

      print(f'money: {self.money}')

  def take_operation_decision(self, actual_market_data, actual_date):
    """Toma la decisión de operación basada en la estrategia de trading.

    Args:
        actual_market_data (DataFrame): Datos del mercado actual.
        actual_date (datetime): Fecha actual.
    """
    ticker = actual_market_data['ticker']

    orders = [order for order in self.orders if order.ticker == ticker]

    action, operation_type, order = self.trading_strategy(
      actual_date,
      actual_market_data, 
      orders,
      self.allowed_days_in_position,
      self.threshold_up,
      self.threshold_down
    )

    print(f'result {action} {operation_type}: {ticker}')

    if action != 'wait':
      price = actual_market_data['Close']
  
      if action == 'open':
        self.open_position(
          type=operation_type, 
          ticker=ticker, 
          date=actual_date, 
          price=price
        )
      elif action == 'close':
        self.close_position(order, date=actual_date, price=price)
  

  def get_orders(self):
    """Obtiene las órdenes de compra y venta realizadas.

    Returns:
        DataFrame: Órdenes de compra.
        DataFrame: Órdenes de venta.
        DataFrame: Estado de la cartera.
    """
    print('saving results')

    df_orders = pd.DataFrame([vars(order) for order in self.orders])


    df_wallet = pd.DataFrame(
      {      
        'date': self.wallet_evolution.keys(), 
        'wallet': self.wallet_evolution.values()
      }
    )

    return df_orders, df_wallet