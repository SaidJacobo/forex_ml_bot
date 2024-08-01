from typing import List
import talib
import numpy as np
from backbone.order import Order
from pandas import DataFrame
from abc import ABC, abstractmethod
from backbone.enums import ActionType
from backbone.utils.general_purpose import get_session, diff_pips
import pandas_ta as ta
import pandas as pd

class ABCTrader(ABC):
  """Agente de Trading para tomar decisiones de compra y venta."""

  def __init__(self, 
               trading_strategy, 
               trading_logic, 
               stop_loss_strategy, 
               take_profit_strategy, 
               threshold:float, 
               allowed_days_in_position:int,
               stop_loss_in_pips:int,
               risk_reward:int,
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
    self.trading_logic = trading_logic
    self.stop_loss_strategy = stop_loss_strategy
    self.take_profit_strategy = take_profit_strategy
    self.threshold = threshold
    self.stop_loss_in_pips = stop_loss_in_pips
    self.risk_reward = risk_reward
    self.risk_percentage = risk_percentage

    self.pips_per_value = pips_per_value
    self.use_trailing_stop = use_trailing_stop
    self.trade_with = trade_with
    self.max_sl_in_pips = 25 / (self.risk_reward - 1) # ADVERTENCIA parametrizar el 25 ademas esta medio dudoso

  def calculate_indicators(self, df:DataFrame, ticker):
    """Calcula indicadores técnicos para el DataFrame dado.

    Args:
        df (DataFrame): DataFrame de datos financieros.

    Returns:
        DataFrame: DataFrame con los indicadores calculados.
    """
    df.sort_values(by='Date', ascending=True, inplace=True)

    df['sma_12'] = talib.SMA(df['Close'], timeperiod=12)
    df['sma_26'] = talib.SMA(df['Close'], timeperiod=26)
    df['sma_50'] = talib.SMA(df['Close'], timeperiod=50)
    df['sma_200'] = talib.SMA(df['Close'], timeperiod=200)

    df['rsi'] = talib.RSI(df['Close'])

    upper_band, middle_band, lower_band = talib.BBANDS(df['Close'], timeperiod=50)
    df['upper_bband'] = upper_band
    df['middle_bband'] = middle_band
    df['lower_bband'] = lower_band

    df['distance_between_bbands'] = (df['upper_bband'] - df['lower_bband']) / self.pips_per_value[ticker]
    df['distance_between_bbands_shift_1'] = df['distance_between_bbands'].shift(1)
    df['distance_between_bbands_shift_2'] = df['distance_between_bbands'].shift(2)
    df['distance_between_bbands_shift_3'] = df['distance_between_bbands'].shift(3)
    df['distance_between_bbands_shift_4'] = df['distance_between_bbands'].shift(4)
    df['distance_between_bbands_shift_5'] = df['distance_between_bbands'].shift(5)

    df['atr'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=14)

    df['mfi'] = talib.MFI(df['High'], df['Low'], df['Close'], df['Volume'], timeperiod=14)


    macd, macdsignal, macdhist = talib.MACD(df['Close'], fastperiod=12, slowperiod=26, signalperiod=9)
    df['macd'] = macd
    df['macdsignal'] = macdsignal
    df['macdhist'] = macdhist

    df['diff_pips_ch'] = (df['Close'] - df['High']) / self.pips_per_value[ticker]
    df['diff_pips_co'] = (df['Close'] - df['Open']) / self.pips_per_value[ticker]
    df['diff_pips_cl'] = (df['Close'] - df['Low']) / self.pips_per_value[ticker]
    df['diff_pips_hl'] = (df['High'] - df['Low']) / self.pips_per_value[ticker]

    df['diff_pips_1_day'] = (df['Close'] - df['Close'].shift(1)) / self.pips_per_value[ticker]
    df['diff_pips_2_day'] = (df['Close'].shift(1) - df['Close'].shift(2)) / self.pips_per_value[ticker]
    df['diff_pips_3_day'] = (df['Close'].shift(2) - df['Close'].shift(3)) / self.pips_per_value[ticker]
    
    df['diff_pips_h'] = (df['High'] - df['High'].shift(1)) / self.pips_per_value[ticker]
    df['diff_pips_h_shift_1'] = (df['High'].shift(1) - df['High'].shift(2)) / self.pips_per_value[ticker]
    df['diff_pips_h_shift_2'] = (df['High'].shift(2) - df['High'].shift(3)) / self.pips_per_value[ticker]
    
    df['diff_pips_o'] = (df['Open'] - df['Open'].shift(1)) / self.pips_per_value[ticker]
    df['diff_pips_o_shift_1'] = (df['Open'].shift(1) - df['Open'].shift(2)) / self.pips_per_value[ticker]
    df['diff_pips_o_shift_2'] = (df['Open'].shift(2) - df['Open'].shift(3)) / self.pips_per_value[ticker]
    
    df['diff_pips_l'] = (df['Low'] - df['Low'].shift(1)) / self.pips_per_value[ticker]
    df['diff_pips_l_shift_1'] = (df['Low'].shift(1) - df['Low'].shift(2)) / self.pips_per_value[ticker]
    df['diff_pips_l_shift_2'] = (df['Low'].shift(2) - df['Low'].shift(3)) / self.pips_per_value[ticker]

    df['hour'] = df.Date.dt.hour 
    df['day'] = df.Date.dt.day 

    sti = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=6)
    # df['adx'] = talib.ADX(df['High'], df['Low'], df['Close'], timeperiod=14)

    df['supertrend'] = sti['SUPERTd_10_6.0']
    df['SUPERT_10_6.0'] = sti['SUPERT_10_6.0']
    df['aroon'] = talib.AROONOSC(df['High'], df['High'], timeperiod=10)

    df['three_stars'] = talib.CDL3STARSINSOUTH(df.Open, df.High, df.Low, df.Close)
    df['closing_marubozu'] = talib.CDLCLOSINGMARUBOZU(df.Open, df.High, df.Low, df.Close)
    df['doji'] = talib.CDLDOJI(df.Open, df.High, df.Low, df.Close)
    df['doji_star'] = talib.CDLDOJISTAR(df.Open, df.High, df.Low, df.Close)
    df['dragon_fly'] = talib.CDLDRAGONFLYDOJI(df.Open, df.High, df.Low, df.Close)
    df['engulfing'] = talib.CDLENGULFING(df.Open, df.High, df.Low, df.Close)
    df['evening_doji_star'] = talib.CDLEVENINGDOJISTAR(df.Open, df.High, df.Low, df.Close)
    df['hammer'] = talib.CDLHAMMER(df.Open, df.High, df.Low, df.Close)
    df['hanging_man'] = talib.CDLHANGINGMAN(df.Open, df.High, df.Low, df.Close)
    df['marubozu'] = talib.CDLMARUBOZU(df.Open, df.High, df.Low, df.Close)
    df['morning_star'] = talib.CDLMORNINGSTAR(df.Open, df.High, df.Low, df.Close)
    df['shooting_star'] = talib.CDLSHOOTINGSTAR(df.Open, df.High, df.Low, df.Close)
    df['inverted_hammer'] = talib.CDLINVERTEDHAMMER(df.Open, df.High, df.Low, df.Close)

    df['morning_star'] = talib.CDLMORNINGSTAR(df.Open, df.High, df.Low, df.Close)
    df['evening_star'] = talib.CDLEVENINGSTAR(df.Open, df.High, df.Low, df.Close)

    df['three_black_crows'] = talib.CDL3BLACKCROWS(df.Open, df.High, df.Low, df.Close)
    df['three_white_soldiers'] = talib.CDL3WHITESOLDIERS(df.Open, df.High, df.Low, df.Close)
     

    window = 24
    rolling_high = df['High'].rolling(window=window).max()
    rolling_low = df['Low'].rolling(window=window).min()
    rolling_close = df['Close'].rolling(window=window).mean()

    # Calcular el punto pivote principal (PP)
    pivot = (rolling_high + rolling_low + rolling_close) / 3

    # Calcular niveles de resistencia y soporte
    df['r1'] = ((2 * pivot) - rolling_low).round(5)
    df['s1'] = ((2 * pivot) - rolling_high).round(5)
    df['r2'] = (pivot + (rolling_high - rolling_low)).round(5)
    df['s2'] = (pivot - (rolling_high - rolling_low)).round(5)
    df['r3'] = (rolling_high + 2 * (pivot - rolling_low)).round(5)
    df['s3'] = (rolling_low - 2 * (rolling_high - pivot)).round(5)

    df['adx'] = talib.ADX(df['High'], df['Low'], df['Close'], timeperiod=14)

    # Daily ADX
    df['daily_date'] = df['Date'].dt.floor('D')
    data_daily = df[['Date','Open','High','Low','Close']].copy()
    data_daily['daily_date'] = data_daily['Date'].dt.floor('D')

    # Agrupar los datos por día y calcular los valores OHLC diarios
    data_daily = data_daily.groupby('daily_date').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last'
    }).reset_index()

    # Calcular el ADX en la temporalidad diaria
    data_daily['daily_adx'] = talib.ADX(data_daily['High'], data_daily['Low'], data_daily['Close'], timeperiod=14)

    # Merge los valores del ADX diario con el DataFrame horario
    df = pd.merge_asof(
        df, 
        data_daily[['daily_date', 'daily_adx']].sort_values('daily_date'), 
        on='daily_date', 
    )

    del data_daily

    df['daily_adx'] = df['daily_adx'].shift(24)

    smi = ta.squeeze(df['High'], df['Low'], df['Close'], LazyBear=True)
    df['SQZ'] = smi['SQZ_20_2.0_20_1.5']
    df['SQZ_ON'] = smi['SQZ_ON']
    df['SQZ_OFF'] = smi['SQZ_OFF']
    df['SQZ_NO'] = smi['SQZ_NO']


    df = df.dropna()

    return df
  
  def calculate_operation_sides(self, instrument):
      window = 3 # las condiciones se deben cumplir en un intervalo de tres horas
      instrument_with_sides = self.trading_strategy(instrument, window=window) 

      return instrument_with_sides

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


  # ADVERTENCIA esto se podria parametrizar en una funcion aparte para probar distintos
  # Metodos de SL
  def _calculate_stop_loss(self, operation_type, market_data, price, ticker):

        price_sl, sl_in_pips = self.stop_loss_strategy(
           operation_type=operation_type, 
           market_data=market_data,
           price=price,
           pip_value=self.pips_per_value[ticker],
           stop_loss_in_pips=self.stop_loss_in_pips
        )

        return price_sl, sl_in_pips
      # pips = self.pips_per_value[ticker]

      # price_sl = None
      # if operation_type == OperationType.BUY:
      #   price_sl = round(market_data.s1 - (self.stop_loss_in_pips * pips), 5)

      #   sl_in_pips = diff_pips(price, price_sl, self.pips_per_value[ticker])
      
      # elif operation_type == OperationType.SELL:
      #   price_sl = round(market_data.r1 + (self.stop_loss_in_pips * pips), 5)

      #   sl_in_pips = diff_pips(price, price_sl, self.pips_per_value[ticker])
        
      # return round(price_sl, 5), sl_in_pips
  

  def _calculate_take_profit(self, operation_type, price, sl_in_pips, ticker):
      
      price_tp = self.take_profit_strategy(
         operation_type=operation_type, 
         price=price,
         risk_reward=self.risk_reward, 
         sl_in_pips=sl_in_pips, 
         pip_value=self.pips_per_value[ticker]
      )

      return price_tp
      # pips = self.pips_per_value[ticker]

      # price_tp = None
      # if operation_type == OperationType.BUY:
      #   price_tp = price + (self.risk_reward * sl_in_pips * pips)
      
      # elif operation_type == OperationType.SELL:
      #   price_tp = price - (self.risk_reward * sl_in_pips * pips)
        
      # return round(price_tp, 5)

  @abstractmethod
  def open_position(self, operation_type:str, ticker:str, date:str, price:float, market_data) -> None:
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
  

  def _update_stop_loss(self, order_id, actual_price, comment):
    if self.use_trailing_stop:
        open_orders = self.get_open_orders(ticket=order_id) # ADVERTENCIA aca le llegaria la orden, no el id para buscarlo
        
        if not open_orders:
            raise ValueError(f"No open orders found for ticket {order_id}")
        
        order = open_orders.pop()

        new_sl = None

        actual_stop_loss_price = order.stop_loss
        pip_value = self.pips_per_value[order.ticker]
        diff = diff_pips(actual_price, actual_stop_loss_price, pip_value)
        
        # menor nunca va a ser pq sino hubiera cerrado la op
        if diff > self.stop_loss_in_pips:
            new_sl = self._calculate_stop_loss(
                operation_type=order.operation_type, 
                price=actual_price, 
                ticker=order.ticker
            )

        if new_sl is not None:
            order.update(sl=new_sl)
            print(f"Updated order {order_id}: new SL = {new_sl}, last price = {actual_price}")
            
            return order
        else:
            print(f"No update needed for order {order_id}: actual price = {actual_price}, last price = {order.last_price}")
        
        return None

  
  def take_operation_decision(self, actual_market_data, actual_date, allowed_time_to_trade):
    """Toma la decisión de operación basada en la estrategia de trading.

    Args:
        actual_market_data (DataFrame): Datos del mercado actual.
        actual_date (datetime): Fecha actual.
    """
    result = None
    ticker = actual_market_data['ticker']
    
    if ticker in self.trade_with:
      open_positions = self.get_open_orders(symbol=ticker) # ADVERTENCIA aca se obtienen las ordenes

      result = self.trading_logic(
        actual_date,
        actual_market_data, 
        open_positions,
        self.allowed_days_in_position,
        self.use_trailing_stop,
        self.threshold,
      )
      print(ticker,  result)
      
      if result.action != ActionType.WAIT:
        price = actual_market_data['Close']
    
        if result.action == ActionType.OPEN and allowed_time_to_trade:
          self.open_position(
            operation_type=result.operation_type, 
            ticker=ticker, 
            date=actual_date, 
            price=price,
            market_data=actual_market_data,
          )
          
        elif result.action == ActionType.CLOSE:
          self.close_position(
            order_id=result.order_id, # pero aca se manda el id, y del otro lado se la vuelve a buscar
            date=actual_date, 
            price=price, 
            comment=result.comment
          )

        elif result.action == ActionType.UPDATE:
          self.update_position(
            order_id=result.order_id, # pero aca se manda el id, y del otro lado se la vuelve a buscar
            actual_price=price, 
            comment=result.comment
          ) 

          # Quiza se puede mandar directamente la orden y listo
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