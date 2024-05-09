import talib
import pandas as pd
import numpy as np
from backbone.order import Order
from pandas import DataFrame

class TradingAgent():
  """Agente de Trading para tomar decisiones de compra y venta."""

  def __init__(self, 
               start_money:float, 
               trading_strategy, 
               threshold_up:int, 
               threshold_down:int, 
               allowed_days_in_position:int,
               stop_loss_in_pips:int,
               take_profit_in_pips:int,
               risk_percentage:int):
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
    self.stop_loss_in_pips = stop_loss_in_pips
    self.take_profit_in_pips = take_profit_in_pips
    self.risk_percentage = risk_percentage
    self.orders = []

    self.pips_per_value = {
          "EURUSD": 0.0001,
          "GBPUSD": 0.0001,
          "USDJPY": 0.01,
          "USDCAD": 0.0001,
          "AUDUSD": 0.0001,
          "USDCHF": 0.0001,

          # Add more currency pairs as needed
      } 

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

    df['change_percent_ch'] = (((df['Close'] - df['High']) / df['Close']) * 100).round(0)
    df['change_percent_co'] = (((df['Close'] - df['Open']) / df['Close']) * 100).round(0)
    df['change_percent_cl'] = (((df['Close'] - df['Low']) / df['Close']) * 100).round(0)

    df['change_percent_1_day'] = (((df['Close'] - df['Close'].shift(1)) / df['Close']) * 100).round(0)
    df['change_percent_2_day'] = (((df['Close'] - df['Close'].shift(2)) / df['Close']) * 100).round(0)
    df['change_percent_3_day'] = (((df['Close'] - df['Close'].shift(3)) / df['Close']) * 100).round(0)

    df['change_percent_h'] = (((df['High'] - df['High'].shift(1)) / df['High']) * 100).round(0)
    df['change_percent_h'] = (((df['High'] - df['High'].shift(2)) / df['High']) * 100).round(0)
    df['change_percent_h'] = (((df['High'] - df['High'].shift(3)) / df['High']) * 100).round(0)
    
    df['change_percent_o'] = (((df['Open'] - df['Open'].shift(1)) / df['Open']) * 100).round(0)
    df['change_percent_o'] = (((df['Open'] - df['Open'].shift(2)) / df['Open']) * 100).round(0)
    df['change_percent_o'] = (((df['Open'] - df['Open'].shift(3)) / df['Open']) * 100).round(0)
    
    df['change_percent_l'] = (((df['Low'] - df['Low'].shift(1)) / df['Low']) * 100).round(0)
    df['change_percent_l'] = (((df['Low'] - df['Low'].shift(2)) / df['Low']) * 100).round(0)
    df['change_percent_l'] = (((df['Low'] - df['Low'].shift(3)) / df['Low']) * 100).round(0)

    df = df.drop(columns=['Open','High','Low', 'spread', 'real_volume'])

    df = df.dropna()

    return df
  
  def _calculate_lot_size(self, account_size, risk_percentage, stop_loss_pips, currency_pair):
      # Get the pip value for the given currency pair
      pip_value = self.pips_per_value.get(currency_pair, None)
      if pip_value is None:
          return "Invalid currency pair"
      
      # Calculate risk in account currency
      account_currency_risk = account_size * (risk_percentage / 100)
      
      # Calculate lot size in units
      lot_size = round(account_currency_risk / (pip_value * stop_loss_pips))
      
      return lot_size

  def _calculate_stop_loss(self, operation_type, price, ticker):
      pips = self.pips_per_value[ticker]

      price_sl = None
      if operation_type == 'buy':
        price_sl = price - (self.stop_loss_in_pips * pips)
      
      elif operation_type == 'sell':
        price_sl = price + (self.stop_loss_in_pips * pips)
        
      return price_sl
  

  def _calculate_take_profit(self, operation_type, price, ticker):
      
      pips = self.pips_per_value[ticker]

      price_tp = None
      if operation_type == 'buy':
        price_tp = price + (self.take_profit_in_pips * pips)
      
      elif operation_type == 'sell':
        price_tp = price - (self.take_profit_in_pips * pips)
        
      return price_tp

  def open_position(self, type, ticker, date, price):
    """Abre una nueva posición de trading.

    Args:
        type: Tipo de operación (compra/venta).
        ticker (str): Ticker financiero.
        date (datetime): Fecha de la operación.
        price (float): Precio de la operación.
    """
    units = self._calculate_lot_size(
       self.money, 
       self.risk_percentage, # parametrizar
       self.stop_loss_in_pips, # parametrizar
       currency_pair=ticker
       )

    price_sl = self._calculate_stop_loss(type, price, ticker)
    price_tp = self._calculate_take_profit(type, price, ticker)

    order = Order(
      order_type=type, 
      ticker=ticker, 
      open_date=date, 
      open_price=price,
      units=units,
      stop_loss=price_sl, # parametrizar
      take_profit=price_tp # parametrizar
    )

    self.orders.append(order)

    print('='*16, f'se abrio una nueva posicion el {date}', '='*16)

  def close_position(self, order:Order, date, price, comment):
    """Cierra una posición de trading.

    Args:
        order (Order): Orden de trading.
        date (datetime): Fecha de cierre de la operación.
        price (float): Precio de cierre de la operación.
    """
    order.close(close_price=price, close_date=date, comment=comment)
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

    action, operation_type, order, comment = self.trading_strategy(
      actual_date,
      actual_market_data, 
      orders,
      self.allowed_days_in_position,
      self.threshold_up,
      self.threshold_down
    )

    print(f'result {action} {operation_type}: {ticker}, {comment}')

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
        self.close_position(order, date=actual_date, price=price, comment=comment)
  

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