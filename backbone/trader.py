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

  def __init__(
        self, 
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
        trade_with:List[str],
        money:float,
        interval:int,
        leverage:int,
        trades_to_increment_risk:int
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
    self.trade_with = trade_with

    self.balance = money
    self.equity = self.balance
    self.margin = 0
    self.free_margin = self.balance
    self.leverage = leverage
    
    self.equity_history = {}
    self.interval = interval
    
    self.trades_to_increment_risk = trades_to_increment_risk
    self.stop_loss = self._calculate_stop_loss()
    self.take_profit = self._calculate_take_profit()



  def calculate_indicators(self, df:DataFrame, ticker):
    """Calcula indicadores técnicos para el DataFrame dado.

    Args:
        df (DataFrame): DataFrame de datos financieros.

    Returns:
        DataFrame: DataFrame con los indicadores calculados.
    """
    df.sort_values(by='Date', ascending=True, inplace=True)

    df['sma_9'] = talib.SMA(df['Close'], timeperiod=9)
    df['sma_12'] = talib.SMA(df['Close'], timeperiod=12)
    df['sma_26'] = talib.SMA(df['Close'], timeperiod=26)
    df['sma_50'] = talib.SMA(df['Close'], timeperiod=50)
    df['sma_200'] = talib.SMA(df['Close'], timeperiod=200)


    # Definir el tamaño de la ventana
    window = 3

    # Detectar máximos y mínimos locales
    df['max'] = df['Close'].rolling(window=window, center=True).apply(lambda x: x.argmax() == (window // 2), raw=True)
    df['min'] = df['Close'].rolling(window=window, center=True).apply(lambda x: x.argmin() == (window // 2), raw=True)

    # Marcar los máximos y mínimos
    df['max'] = df['max'].astype(bool) * df['Close']
    df['min'] = df['min'].astype(bool) * df['Close']

    # Eliminar ceros para mejor visualización
    df['max'].replace(0, np.nan, inplace=True)
    df['min'].replace(0, np.nan, inplace=True)

    # Crear la columna 'max_min'
    df['max_min'] = 0
    df.loc[df['max'].notna(), 'max_min'] = 1
    df.loc[df['min'].notna(), 'max_min'] = -1

    df['max_min'] = df['max_min'].shift(1)


    del df['max']
    del df['min']

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
    
    data_daily['daily_sma_26'] = talib.SMA(data_daily['Close'], timeperiod=26)

    # Merge los valores del ADX diario con el DataFrame horario
    df = pd.merge_asof(
        df, 
        data_daily[['daily_date', 'daily_adx', 'daily_sma_26']].sort_values('daily_date'), 
        on='daily_date', 
    )

    del data_daily
    del df['daily_date']

    df['daily_adx'] = df['daily_adx'].shift(24)
    df['daily_sma_26'] = df['daily_sma_26'].shift(24)

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

  def _calculate_units_size(self, price, ticker, get_result_in_lots=False):
        open_positions = self.get_open_orders(symbol=ticker)

        # Ajustar el porcentaje de riesgo basado en las posiciones abiertas
        risk_percentage = (len(open_positions) - self.trades_to_increment_risk) * 1.5

        risk_percentage = 1 if risk_percentage <= 0 else risk_percentage

        # Calcular unidades y valor total de la posición
        units = (self.balance * (risk_percentage / 100)) * self.leverage / price
        total_value = price * units

        # Calcular el margen requerido
        margin_required = total_value / self.leverage

        if get_result_in_lots:
          lot_size = 100000
          number_of_lots = round(units / lot_size, 2)
          
          return number_of_lots, margin_required

        return units, margin_required


  def _calculate_stop_loss(self):
        money_stop_loss = self.stop_loss_strategy(
           balance=self.balance,
           risk_percentage=self.risk_percentage
        )

        return money_stop_loss
 

  def _calculate_take_profit(self):
      
      money_take_profit = self.take_profit_strategy(
         balance=self.balance,
        #  risk_percentage=self.risk_percentage,
         risk_percentage=1,
         risk_reward=self.risk_reward
      )

      return money_take_profit


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

  def close_all_positions(self, positions, date:str, price:float, comment:str) -> None:
    """Cierra una posición de trading.

    Args:
        order (Order): Orden de trading.
        date (datetime): Fecha de cierre de la operación.
        price (float): Precio de cierre de la operación.
    """
    pass

  
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
        self.threshold,
        self.take_profit,
        self.stop_loss,
        self.interval
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

        elif result.action == ActionType.CLOSE_ALL:

          self.close_all_positions(
            positions=open_positions,
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

  def update_equity(self, date, actual_price):
    total_profit = 0
    for order in self.get_open_orders():
      money, _ = order.get_profit(actual_price)
      total_profit += money
    
    self.equity = self.balance + total_profit

    self.equity_history[date] = self.equity

    return self.equity
       
        