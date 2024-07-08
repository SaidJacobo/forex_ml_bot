from typing import List
import talib
import numpy as np
from backbone.order import Order
from pandas import DataFrame
from abc import ABC, abstractmethod
from backbone.enums import ActionType, OperationType
from backbone.utils import get_session
from statsmodels.tsa.filters.hp_filter import hpfilter


class ABCTrader(ABC):
  """Agente de Trading para tomar decisiones de compra y venta."""

  def __init__(self, 
               trading_strategy, 
               threshold:float, 
               allowed_days_in_position:int,
               stop_loss_in_pips:int,
               take_profit_in_pips:int,
               risk_percentage:int,
               allowed_sessions:List[str],
               pips_per_value:dict,
               use_trailing_stop:bool,
               trade_with:List[str]
    ):
    """
    Inicializa el Agente de Trading.
    Args:
        start_money (float): Dinero inicial para realizar las operaciones.
        trading_strategy: Estrategia de trading.
        threshold (int): Umbral superior.
        allowed_days_in_position (int): Días permitidos en una posición.
    """
    self.allowed_sessions = allowed_sessions
    self.allowed_days_in_position = allowed_days_in_position
    self.trading_strategy = trading_strategy
    self.threshold = threshold
    self.stop_loss_in_pips = stop_loss_in_pips
    self.take_profit_in_pips = take_profit_in_pips
    self.risk_percentage = risk_percentage

    self.pips_per_value = pips_per_value
    self.use_trailing_stop = use_trailing_stop
    self.trade_with = trade_with
  
  def calculate_indicators(self, df:DataFrame):
    """Calcula indicadores técnicos para el DataFrame dado.

    Args:
        df (DataFrame): DataFrame de datos financieros.

    Returns:
        DataFrame: DataFrame con los indicadores calculados.
    """
    df.sort_values(by='Date', ascending=True, inplace=True)

    df['ema_12'] = talib.EMA(df['Close'], timeperiod=12)
    df['ema_26'] = talib.EMA(df['Close'], timeperiod=26)
    df['ema_50'] = talib.EMA(df['Close'], timeperiod=50)
    df['ema_200'] = talib.EMA(df['Close'], timeperiod=200)

    # Cruce positivo
    df['ema_flag'] = 0
    df['ema_flag'] = np.where(
      (df['ema_12'] > df['ema_200']) 
      & (df['ema_12'].shift(1) <= df['ema_200'].shift(1)), 
      1, 
      df['ema_flag']
    )

    # Cruce negativo
    df['ema_flag'] = np.where(
      (df['ema_12'] < df['ema_200']) 
      & (df['ema_12'].shift(1) >= df['ema_200'].shift(1)), 
      -1, 
      df['ema_flag']
    )

    df['rsi'] = talib.RSI(df['Close'])
    df['rsi_flag'] = 0
    df['rsi_flag'] = np.where((df['rsi'] > 70), -1, df['rsi_flag'])
    df['rsi_flag'] = np.where((df['rsi'] < 30), 1, df['rsi_flag'])

    upper_band, middle_band, lower_band = talib.BBANDS(df['Close'], timeperiod=50)
    df['upper_bband'] = upper_band
    df['middle_bband'] = middle_band
    df['lower_bband'] = lower_band

    df['bband_flag'] = 0
    df['bband_flag'] = np.where((df['Close'] > df['upper_bband']), 1, df['bband_flag']) 
    df['bband_flag'] = np.where((df['Close'] < df['lower_bband']), -1, df['bband_flag']) 

    df['atr'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=14)

    df['mfi'] = talib.MFI(df['High'], df['Low'], df['Close'], df['Volume'], timeperiod=14)

    df['adx'] = talib.ADX(df['High'], df['Low'], df['Close'], timeperiod=14)

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

    df['hour'] = df.Date.dt.hour 
    df['day'] = df.Date.dt.day 

    df['day'] = df.Date.dt.day 

    df['closing_marubozu'] = talib.CDLCLOSINGMARUBOZU(df.Open, df.High, df.Low, df.Close)
    df['doji'] = talib.CDLDOJI(df.Open, df.High, df.Low, df.Close)
    df['engulfing'] = talib.CDLENGULFING(df.Open, df.High, df.Low, df.Close)
    df['hammer'] = talib.CDLHAMMER(df.Open, df.High, df.Low, df.Close)
    df['hanging_man'] = talib.CDLHANGINGMAN(df.Open, df.High, df.Low, df.Close)
    df['marubozu'] = talib.CDLMARUBOZU(df.Open, df.High, df.Low, df.Close)
    df['shooting_star'] = talib.CDLSHOOTINGSTAR(df.Open, df.High, df.Low, df.Close)

    _, trend = hpfilter(df['Close'], lamb=1000)
    df['trend'] = trend
    df['SMA20'] = df['trend'].rolling(window=20).mean()

    df = df.drop(columns=['spread', 'real_volume'])

    df = df.dropna()

    return df
  
  def calculate_operation_sides(self, instrument):
      # Esto deberia estar parametrizado
      long_signals = (instrument['trend'] > instrument['SMA20']) & (instrument['trend'].shift(1) <= instrument['SMA20'].shift(1))
      short_signals = (instrument['trend'] < instrument['SMA20']) & (instrument['trend'].shift(1) >= instrument['SMA20'].shift(1))
      instrument.loc[long_signals, 'side'] = 1
      instrument.loc[short_signals, 'side'] = -1

      print(instrument.side.value_counts())

      # Remove Look ahead biase by lagging the signal
      # instrument['side'] = instrument['side'].shift(1)
      
      # Drop the NaN values from our data set
      instrument.dropna(inplace=True)

      return instrument

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
    units = self._calculate_units_size(
      account_size, 
      risk_percentage, 
      stop_loss_pips, 
      currency_pair, 
    )
    
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
        
      return round(price_sl, 4)
  

  def _calculate_take_profit(self, operation_type, price, ticker):
      
      pips = self.pips_per_value[ticker]

      price_tp = None
      if operation_type == OperationType.BUY:
        price_tp = price + (self.take_profit_in_pips * pips)
      
      elif operation_type == OperationType.SELL:
        price_tp = price - (self.take_profit_in_pips * pips)
        
      return round(price_tp, 4)

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

  
  @abstractmethod
  def update_position(self, order_id, actual_price, comment):
    pass

  
  def take_operation_decision(self, actual_market_data, actual_date):
    """Toma la decisión de operación basada en la estrategia de trading.

    Args:
        actual_market_data (DataFrame): Datos del mercado actual.
        actual_date (datetime): Fecha actual.
    """
    result = None
    ticker = actual_market_data['ticker']
    
    if ticker in self.trade_with:
      open_positions = self.get_open_orders(symbol=ticker)

      result = self.trading_strategy(
        actual_date,
        actual_market_data, 
        open_positions,
        self.allowed_days_in_position,
        self.use_trailing_stop,
        self.threshold,
      )
      print(ticker,  result)
      actual_session = get_session(actual_date)
      
      if result.action != ActionType.WAIT:
        price = actual_market_data['Close']
    
        if result.action == ActionType.OPEN and actual_session in self.allowed_sessions:
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

        elif result.action == ActionType.UPDATE:
          self.update_position(
            order_id=result.order_id, 
            actual_price=price, 
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