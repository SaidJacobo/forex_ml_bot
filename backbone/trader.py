from typing import List
import talib
import numpy as np
from backbone.order import Order
from pandas import DataFrame
from abc import ABC, abstractmethod
from backbone.enums import ActionType, OperationType

class ABCTrader(ABC):
  """Agente de Trading para tomar decisiones de compra y venta."""

  def __init__(self, 
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
    self.allowed_days_in_position = allowed_days_in_position
    self.trading_strategy = trading_strategy
    self.threshold_up = threshold_up
    self.threshold_down = threshold_down
    self.stop_loss_in_pips = stop_loss_in_pips
    self.take_profit_in_pips = take_profit_in_pips
    self.risk_percentage = risk_percentage

    self.pips_per_value = {
          "EURUSD": 0.0001,
          "GBPUSD": 0.0001,
          "USDJPY": 0.01,
          "USDCAD": 0.0001,
          "AUDUSD": 0.0001,
          "USDCHF": 0.0001,
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

    df['change_percent_ch'] = (((df['Close'] - df['High']) / df['Close']) * 100).round(2)
    df['change_percent_co'] = (((df['Close'] - df['Open']) / df['Close']) * 100).round(2)
    df['change_percent_cl'] = (((df['Close'] - df['Low']) / df['Close']) * 100).round(2)

    df['change_percent_1_day'] = (((df['Close'] - df['Close'].shift(1)) / df['Close']) * 100).round(2)
    df['change_percent_2_day'] = (((df['Close'] - df['Close'].shift(2)) / df['Close']) * 100).round(2)
    df['change_percent_3_day'] = (((df['Close'] - df['Close'].shift(3)) / df['Close']) * 100).round(2)

    df['change_percent_h'] = (((df['High'] - df['High'].shift(1)) / df['High']) * 100).round(2)
    df['change_percent_h'] = (((df['High'] - df['High'].shift(2)) / df['High']) * 100).round(2)
    df['change_percent_h'] = (((df['High'] - df['High'].shift(3)) / df['High']) * 100).round(2)
    
    df['change_percent_o'] = (((df['Open'] - df['Open'].shift(1)) / df['Open']) * 100).round(2)
    df['change_percent_o'] = (((df['Open'] - df['Open'].shift(2)) / df['Open']) * 100).round(2)
    df['change_percent_o'] = (((df['Open'] - df['Open'].shift(3)) / df['Open']) * 100).round(2)
    
    df['change_percent_l'] = (((df['Low'] - df['Low'].shift(1)) / df['Low']) * 100).round(2)
    df['change_percent_l'] = (((df['Low'] - df['Low'].shift(2)) / df['Low']) * 100).round(2)
    df['change_percent_l'] = (((df['Low'] - df['Low'].shift(3)) / df['Low']) * 100).round(2)

    df = df.drop(columns=['spread', 'real_volume'])

    df = df.dropna()

    return df
  
  def _calculate_units_size(self, account_size, risk_percentage, stop_loss_pips, currency_pair):
      # Get the pip value for the given currency pair
      pip_value = self.pips_per_value.get(currency_pair, None)
      if pip_value is None:
          raise Exception(f'No existe valor de pip para el par {currency_pair}')
      
      # Calculate risk in account currency
      account_currency_risk = account_size * (risk_percentage / 100)
      
      # Calculate lot size in units
      units = round(account_currency_risk / (pip_value * stop_loss_pips))
      
      return units


  def _calculate_lot_size(self, account_size, risk_percentage, stop_loss_pips, currency_pair, lot_size_standard):
    units = self._calculate_units_size(account_size, risk_percentage, stop_loss_pips, currency_pair)
    
    decimals = 2
    number_of_lots = round(units / lot_size_standard, decimals)
    
    return number_of_lots

  def _calculate_stop_loss(self, operation_type, price, ticker):
      pips = self.pips_per_value[ticker]

      price_sl = None
      if operation_type == OperationType.BUY:
        price_sl = price - (self.stop_loss_in_pips * pips)
      
      elif operation_type == OperationType.SELL:
        price_sl = price + (self.stop_loss_in_pips * pips)
        
      return price_sl
  

  def _calculate_take_profit(self, operation_type, price, ticker):
      
      pips = self.pips_per_value[ticker]

      price_tp = None
      if operation_type == OperationType.BUY:
        price_tp = price + (self.take_profit_in_pips * pips)
      
      elif operation_type == OperationType.SELL:
        price_tp = price - (self.take_profit_in_pips * pips)
        
      return price_tp

  @abstractmethod
  def open_position(self, operation_type:str, ticker:str, date:str, price:float) -> None:
    """Abre una nueva posición de trading.

    Args:
        type: Tipo de operación (compra/venta).
        ticker (str): Ticker financiero.
        date (datetime): Fecha de la operación.
        price (float): Precio de la operación.
    """
    pass

  @abstractmethod
  def close_position(self, order_id:int, date:str, price:float, comment:str) -> None:
    """Cierra una posición de trading.

    Args:
        order (Order): Orden de trading.
        date (datetime): Fecha de cierre de la operación.
        price (float): Precio de cierre de la operación.
    """
    pass


  def take_operation_decision(self, actual_market_data, actual_date):
    """Toma la decisión de operación basada en la estrategia de trading.

    Args:
        actual_market_data (DataFrame): Datos del mercado actual.
        actual_date (datetime): Fecha actual.
    """
    ticker = actual_market_data['ticker']
    
    open_positions = self.get_open_orders(symbol=ticker)

    result = self.trading_strategy(
      actual_date,
      actual_market_data, 
      open_positions,
      self.allowed_days_in_position,
      self.threshold_up,
      self.threshold_down
    )
    print(ticker,  result)
    if result.action != ActionType.WAIT:
      price = actual_market_data['Close']
  
      if result.action == ActionType.OPEN:
        self.open_position(
          operation_type=result.operation_type, 
          ticker=ticker, 
          date=actual_date, 
          price=price
        )
        
      elif result.action == ActionType.CLOSE:
        self.close_position(
          order_id=result.order_id, 
          date=actual_date, 
          price=price, 
          comment=result.comment
        )
    
    return result
  
  @abstractmethod
  def get_open_orders(self, ticket:int=None, symbol:str=None) -> List[Order]:
    """Obtiene las órdenes de compra y venta realizadas.

    Returns:
        DataFrame: Órdenes de compra.
        DataFrame: Órdenes de venta.
        DataFrame: Estado de la cartera.
    """
    pass