from typing import List
import talib
import numpy as np
from backbone.order import Order
from pandas import DataFrame
from abc import ABC, abstractmethod
from backbone.enums import ActionType, OperationType
from backbone.utils.general_purpose import get_session, diff_pips
import pandas_ta as ta
import pandas as pd


class RMITrendSniper:
    def __init__(self, length=14, positive_above=66, negative_below=30, ema_length=5):
        self.length = length
        self.positive_above = positive_above
        self.negative_below = negative_below
        self.ema_length = ema_length
    
    def calculate_rmi(self, df):
        # Calcula el RSI
        data = df.copy()
        delta = data['Close'].diff()
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        avg_gain = pd.Series(gain).rolling(window=self.length, min_periods=1).mean()
        avg_loss = pd.Series(loss).rolling(window=self.length, min_periods=1).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # Calcula el MFI (Money Flow Index)
        typical_price = (data['High'] + data['Low'] + data['Close']) / 3
        money_flow = typical_price * data['Volume']
        pos_flow = np.where(typical_price > typical_price.shift(1), money_flow, 0)
        neg_flow = np.where(typical_price < typical_price.shift(1), money_flow, 0)
        pos_mf = pd.Series(pos_flow).rolling(window=self.length, min_periods=1).sum()
        neg_mf = pd.Series(neg_flow).rolling(window=self.length, min_periods=1).sum()
        mfi = 100 - (100 / (1 + pos_mf / neg_mf))
        
        # Calcula RMI-MFI
        rmi_mfi = (rsi + mfi) / 2
        
        return rmi_mfi
    
    def calculate_signals(self, data):
        rmi_mfi = self.calculate_rmi(data)
        ema = data['Close'].ewm(span=self.ema_length, adjust=False).mean()
        ema_change = ema.diff()

        p_mom = (rmi_mfi.shift(1) < self.positive_above) & (rmi_mfi > self.positive_above) & (rmi_mfi > self.negative_below) & (ema_change > 0)
        n_mom = (rmi_mfi < self.negative_below) & (ema_change < 0)
        
        # Definir las condiciones de momento positivo y negativo
        data['signal'] = 0
        data.loc[p_mom, 'signal'] = 1
        data.loc[n_mom, 'signal'] = -1
        
        return data.signal
    
    def apply(self, data):
        data = self.calculate_signals(data)
        return data

def bollinger_bands_filter(df, length=55, mult=1.0, close_col='Close'):
    # Calcular la media móvil simple (SMA)
    sma = df[close_col].rolling(window=length).mean()
    
    # Calcular la desviación estándar
    std_dev = df[close_col].rolling(window=length).std()
    
    # Calcular las Bandas de Bollinger
    upper_band = sma + (mult * std_dev)
    lower_band = sma - (mult * std_dev)
    
    # Condiciones de compra y venta
    long = df[close_col] > upper_band
    short = df[close_col] < lower_band
    
    # Convertir a booleanos
    long = long.astype(bool)
    short = short.astype(bool)
    
    # Señales de compra y venta
    long_signal = long & ~long.shift(1).astype(bool)
    short_signal = short & ~short.shift(1).astype(bool)

    signal = np.zeros(df.shape[0])
    
    signal = np.where(((long_signal == True) ), 1, signal)
    signal = np.where(((short_signal == True) ), -1, signal)

    return signal


class ABCTrader(ABC):
  """Agente de Trading para tomar decisiones de compra y venta."""

  def __init__(
        self, 
        trading_strategy, 
        money:float
    ):
    """
    Inicializa el Agente de Trading.
    Args:
        start_money (float): Dinero inicial para realizar las operaciones.
        trading_strategy: Estrategia de trading.
        threshold (int): Umbral superior.
        allowed_days_in_position (int): Días permitidos en una posición.
    """
    self.trading_strategy = trading_strategy
    self.balance = money
    self.equity = self.balance
    self.margin = 0
    self.free_margin = self.balance
    self.equity_history = {}
    self.positions : List[Order] = []


  def calculate_indicators(self, df:DataFrame, ticker):
    """Calcula indicadores técnicos para el DataFrame dado.

    Args:
        df (DataFrame): DataFrame de datos financieros.

    Returns:
        DataFrame: DataFrame con los indicadores calculados.
    """
    df.sort_values(by='Date', ascending=True, inplace=True)

    df['sma_5'] = talib.SMA(df['Close'], timeperiod=5)
    df['sma_9'] = talib.SMA(df['Close'], timeperiod=9)
    df['sma_12'] = talib.SMA(df['Close'], timeperiod=12)
    df['sma_26'] = talib.SMA(df['Close'], timeperiod=26)
    df['sma_50'] = talib.SMA(df['Close'], timeperiod=50)
    df['sma_200'] = talib.SMA(df['Close'], timeperiod=200)
    
    value_pip = self.trading_strategy.pip_value

    df['diff_pips_sma_200_26'] = df.apply(
        lambda row: diff_pips(row['sma_200'], row['sma_26'], pip_value=value_pip), 
        axis=1
    )

    macd, macdsignal, macdhist = talib.MACD(df['Close'], fastperiod=12, slowperiod=26, signalperiod=9)
    df['macd'] = macd
    df['macdsignal'] = macdsignal
    df['macdhist'] = macdhist

    df['bband_filter_signal'] = bollinger_bands_filter(df)

    df['atr'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=14)

    rmi_trend_sniper = RMITrendSniper()
    df['rmi_signal'] = rmi_trend_sniper.apply(df)

    # Definir el tamaño de la ventana
    window = 3

    # Detectar máximos y mínimos locales
    df['max'] = df['sma_5'].rolling(window=window, center=True).apply(lambda x: x.argmax() == (window // 2), raw=True)
    df['min'] = df['sma_5'].rolling(window=window, center=True).apply(lambda x: x.argmin() == (window // 2), raw=True)

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


    df['distance_between_bbands'] = (df['upper_bband'] - df['lower_bband']) / value_pip
    df['distance_between_bbands_shift_1'] = df['distance_between_bbands'].shift(1)
    df['distance_between_bbands_shift_2'] = df['distance_between_bbands'].shift(2)
    df['distance_between_bbands_shift_3'] = df['distance_between_bbands'].shift(3)
    df['distance_between_bbands_shift_4'] = df['distance_between_bbands'].shift(4)
    df['distance_between_bbands_shift_5'] = df['distance_between_bbands'].shift(5)

    df['diff_pips_ch'] = (df['Close'] - df['High']) / value_pip
    df['diff_pips_co'] = (df['Close'] - df['Open']) / value_pip
    df['diff_pips_cl'] = (df['Close'] - df['Low']) / value_pip
    df['diff_pips_hl'] = (df['High'] - df['Low']) / value_pip

    df['diff_pips_1_day'] = (df['Close'] - df['Close'].shift(1)) / value_pip
    df['diff_pips_2_day'] = (df['Close'].shift(1) - df['Close'].shift(2)) / value_pip
    df['diff_pips_3_day'] = (df['Close'].shift(2) - df['Close'].shift(3)) / value_pip
    
    df['diff_pips_h'] = (df['High'] - df['High'].shift(1)) / value_pip
    df['diff_pips_h_shift_1'] = (df['High'].shift(1) - df['High'].shift(2)) / value_pip
    df['diff_pips_h_shift_2'] = (df['High'].shift(2) - df['High'].shift(3)) / value_pip
    
    df['diff_pips_o'] = (df['Open'] - df['Open'].shift(1)) / value_pip
    df['diff_pips_o_shift_1'] = (df['Open'].shift(1) - df['Open'].shift(2)) / value_pip
    df['diff_pips_o_shift_2'] = (df['Open'].shift(2) - df['Open'].shift(3)) / value_pip
    
    df['diff_pips_l'] = (df['Low'] - df['Low'].shift(1)) / value_pip
    df['diff_pips_l_shift_1'] = (df['Low'].shift(1) - df['Low'].shift(2)) / value_pip
    df['diff_pips_l_shift_2'] = (df['Low'].shift(2) - df['Low'].shift(3)) / value_pip

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

    # Calcular niveles de resistencia y soporte
    df['r1'] = df['High'].rolling(window=8).max().shift(1)
    df['s1'] = df['Low'].rolling(window=8).min().shift(1)

    df['r2'] = df['High'].rolling(window=24).max().shift(1)
    df['s2'] = df['Low'].rolling(window=24).min().shift(1)

    df['r3'] = df['High'].rolling(window=48).max().shift(1)
    df['s3'] = df['Low'].rolling(window=48).min().shift(1)

    df['adx'] = talib.ADX(df['High'], df['Low'], df['Close'], timeperiod=14)

    # Daily ADX
    # df['daily_date'] = df['Date'].dt.floor('D')
    # data_daily = df[['Date','Open','High','Low','Close']].copy()
    # data_daily['daily_date'] = data_daily['Date'].dt.floor('D')

    # # Agrupar los datos por día y calcular los valores OHLC diarios
    # data_daily = data_daily.groupby('daily_date').agg({
    #     'Open': 'first',
    #     'High': 'max',
    #     'Low': 'min',
    #     'Close': 'last'
    # }).reset_index()

    # # Calcular el ADX en la temporalidad diaria
    # data_daily['daily_adx'] = talib.ADX(data_daily['High'], data_daily['Low'], data_daily['Close'], timeperiod=14)
    
    # data_daily['daily_sma_26'] = talib.SMA(data_daily['Close'], timeperiod=26)

    # # Merge los valores del ADX diario con el DataFrame horario
    # df = pd.merge_asof(
    #     df, 
    #     data_daily[['daily_date', 'daily_adx', 'daily_sma_26']].sort_values('daily_date'), 
    #     on='daily_date', 
    # )

    # del data_daily
    # del df['daily_date']

    # df['daily_adx'] = df['daily_adx'].shift(24)
    # df['daily_sma_26'] = df['daily_sma_26'].shift(24)

    smi = ta.squeeze(df['High'], df['Low'], df['Close'], LazyBear=True)
    df['SQZ'] = smi['SQZ_20_2.0_20_1.5']
    df['SQZ_ON'] = smi['SQZ_ON']
    df['SQZ_OFF'] = smi['SQZ_OFF']
    df['SQZ_NO'] = smi['SQZ_NO']

    df['engulfing'] = 0

    df['engulfing'] = np.where(
        (df['Close'] > df['Open']) # Vela alcista
        & (df['Close'].shift(1) < df['Open'].shift(1)) # Vela bajista
        & (df['Close'] >= df['Open'].shift(1)) # Cierre de la vela alcista por encima del high de la vela bajista anterior
        , 1, df['engulfing']
    )

    df['engulfing'] = np.where(
        (df['Close'] < df['Open']) # Vela bajista
        & (df['Close'].shift(1) > df['Open'].shift(1)) # Vela alcista
        & (df['Close'] <= df['Open'].shift(1)) # Cierre de la vela bajista por debajo del low de la vela alcista anterior
        , -1
        , df['engulfing']
    )

    df['direction'] = df['Close'] > df['Open']
    df['direction'] = df['direction'].map({True: 'Bullish', False: 'Bearish'})

    df['Group'] = (df['direction'] != df['direction'].shift()).cumsum()
    df['consecutive_candles'] = df.groupby('Group').cumcount() + 1

    # quantile = 0.3
    # range_ = df['High'] - df['Low']
    # acum_threshold = range_.rolling(window=24, min_periods=1).apply(lambda x: x.quantile(quantile), raw=False)
    # df['is_acumulation'] = range_ < acum_threshold
    # df['is_acumulation'] = df['is_acumulation']

    df = df.dropna()

    return df
  
  def calculate_operation_sides(self, instrument):
      window = 3 # las condiciones se deben cumplir en un intervalo de tres horas
      instrument_with_sides = self.trading_strategy.calculate_operation_sides(instrument) 

      return instrument_with_sides


  @abstractmethod
  def open_position(
        self,
        today,
        operation_type:OperationType,
        units:int,
        lots:float,
        sl:int,
        tp:int,
        margin_required:int,
        price:float 
  ) -> None:
    """Abre una nueva posición de trading.

    Args:
        type: Tipo de operación (compra/venta).
        ticker (str): Ticker financiero.
        date (datetime): Fecha de la operación.
        price (float): Precio de la operación.
    """
    pass

  @abstractmethod
  def close_position(self, oerders, date:str, price:float, comment:str) -> None:
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

  
  def take_operation_decision(self, actual_market_data, actual_date, allowed_time_to_trade, price=None):
    """Toma la decisión de operación basada en la estrategia de trading.

    Args:
        actual_market_data (DataFrame): Datos del mercado actual.
        actual_date (datetime): Fecha actual.
    """
    result = None
    ticker = actual_market_data['ticker']
    
    open_positions = self.get_open_orders(symbol=ticker) # ADVERTENCIA aca se obtienen las ordenes
    
    result = self.trading_strategy.order_management(
      today=actual_date, 
      market_data=actual_market_data, 
      total_orders=self.positions, 
      balance=self.balance, 
      equity=self.equity, 
      margin=self.margin, 
      price=price,
    )

    for action, values in result.items():
      if action == ActionType.CLOSE and values:
        self.close_position(
          orders_package=values,
          date=actual_date, 
          price=price, 
          comment=''
        )
  
      if action == ActionType.OPEN and values:
        operation_type, units, lots, tp, sl, margin_required = values
        self.open_position(
          today=actual_date,
          operation_type=operation_type,
          units=units,
          lots=lots,
          sl=sl,
          tp=tp,
          margin_required=margin_required,
          price=price
        )
        

      if action == ActionType.UPDATE and values:
        self.update_position(
          orders_package=values,
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

  def update_equity(self, date, actual_price):
    total_profit = 0
    for order in self.get_open_orders():
      money, _ = order.get_profit(actual_price)
      total_profit += money
    
    self.equity = self.balance + total_profit

    self.equity_history[date] = self.equity

    return self.equity
       
        