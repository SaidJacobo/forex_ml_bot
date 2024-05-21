from backbone.machine_learning_agent import MachineLearningAgent
from backbone.trader import ABCTrader
import pandas as pd
import os
import MetaTrader5 as mt5
import pytz
from datetime import datetime
from datetime import timedelta
from backbone.utils import write_in_logs


class Botardo():
  """Clase base de bot de trading y aprendizaje automático.

  Attributes:
      ml_agent (MachineLearningAgent): Agente de Aprendizaje Automático.
      trading_agent (TradingAgent): Agente de Trading.
      tickers (list): Lista de tickers financieros.
      instruments (dict): Diccionario que contiene los datos de los instrumentos financieros.
  """
  def __init__(self, tickers:list, ml_agent:MachineLearningAgent, trader:ABCTrader):
    """Inicializa un nuevo objeto Botardo.

    Args:
        tickers (list): Lista de tickers financieros.
        ml_agent (MachineLearningAgent): Agente de Aprendizaje Automático.
        trading_agent (TradingAgent): Agente de Trading.
    """
    self.ml_agent = ml_agent
    self.trader = trader
    self.tickers = tickers
    self.instruments = {}
    self.date_format = '%Y-%m-%d %H:00:00'


  def _get_symbols_from_provider(self, date_from:str, date_to:str, ticker:str) -> None:
    print("MetaTrader5 package author: ", mt5.__author__)
    print("MetaTrader5 package version: ", mt5.__version__)

    # establish connection to MetaTrader 5 terminal
    if not mt5.initialize():
        raise Exception("initialize() failed, error code =",mt5.last_error())

    # set time zone to UTC
    timezone = pytz.timezone("Etc/UTC")

    # create 'datetime' objects in UTC time zone to avoid the implementation of a local time zone offset
    utc_from = datetime.strptime(date_from, self.date_format).replace(tzinfo=timezone)
    utc_to = datetime.strptime(date_to, self.date_format).replace(tzinfo=timezone)

    # get bars from USDJPY M5 within the interval of 2020.01.10 00:00 - 2020.01.11 13:00 in UTC time zone
    rates = mt5.copy_rates_range(ticker, mt5.TIMEFRAME_H1, utc_from, utc_to)

    # shut down connection to the MetaTrader 5 terminal
    mt5.shutdown()

    # create DataFrame out of the obtained data
    df = pd.DataFrame(rates)

    # convert time in seconds into the datetime format
    df['time'] = pd.to_datetime(df['time'], unit='s')
                              
    df = df.rename(columns={
      'time':'Date', 
      'open':'Open', 
      'high':'High', 
      'low':'Low', 
      'close':'Close', 
      'tick_volume':'Volume'
    })

    self.instruments[ticker] = df
    self.instruments[ticker]['Date'] = self.instruments[ticker]['Date']    

  def get_symbols_and_generate_indicators(
      self, 
      symbols_path:str, 
      date_from:datetime, 
      date_to:datetime, 
      save=True,
      force_download=False
    ) -> None:
    """Crea el conjunto de datos para el backtesting.

    Args:
        symbols_path (str): Ruta donde se guardarán los datos.
        date_from (str): Fecha de inicio del periodo de datos históricos.
        date_to (str): Fecha de fin del periodo de datos históricos.
    """
    date_from = date_from.strftime(self.date_format)
    date_to = date_to.strftime(self.date_format)

    for ticker in self.tickers:
      if force_download:
          print(f'descargando simbolo: {ticker}')
          self._get_symbols_from_provider(
            date_from, 
            date_to, 
            ticker
          )

      else:
        try:
          print(f'Intentando levantar el simbolo {ticker}')
          self.instruments[ticker] = pd.read_csv(os.path.join(symbols_path, f'{ticker}.csv'))
          self.instruments[ticker]['Date'] = pd.to_datetime(self.instruments[ticker]['Date'], format=self.date_format)

          continue

        except FileNotFoundError:
          print(f'No se encontro el simbolo {ticker}. Descargandolo del proveedor')
          self._get_symbols_from_provider(
            date_from, 
            date_to, 
            ticker
          )
        
      self.instruments[ticker]['Date'] = pd.to_datetime(self.instruments[ticker]['Date'], format=self.date_format)
      print(self.instruments[ticker].tail(5))

      print('='*16, f'calculando indicadores para el simbolo {ticker}', '='*16)
      self.instruments[ticker] = self.trader.calculate_indicators(self.instruments[ticker])
      
      if save:
        self.instruments[ticker].to_csv(
          os.path.join(symbols_path, f'{ticker}.csv'), 
          index=False
        )
        
        print(f'Dataset {ticker} guardado correctamente')
  

  def generate_dataset(
      self, 
      symbols_path:str, 
      period_forward_target:int, 
      save=False, 
      load_symbols_from_disk=True,
      drop_nulls=True
    ) -> pd.DataFrame:
    """Genera un conjunto de datos para el backtesting.

    Args:
        symbols_path (str): Ruta donde se encuentran los datos de los instrumentos financieros.
        period_forward_target (int): Periodo de tiempo hacia adelante para calcular el objetivo de predicción.
        save (bool, optional): Indica si se debe guardar el conjunto de datos generado en un archivo CSV. Por defecto es False.

    Returns:
        DataFrame: Conjunto de datos generado.
    """
    df = pd.DataFrame()

    for ticker in self.tickers:
      if load_symbols_from_disk:
        self.instruments[ticker] = pd.read_csv(os.path.join(symbols_path, f'{ticker}.csv'))
      
      self.instruments[ticker]['ticker'] = ticker
      
      print('Creando target')
      self.instruments[ticker] = self.instruments[ticker].sort_values(by='Date')
      self.instruments[ticker]['target'] = ((self.instruments[ticker]['Close'].shift(-period_forward_target) - self.instruments[ticker]['Close']) / self.instruments[ticker]['Close']) * 100

      bins = [-1, 0, 1]
      labels = [0, 1]

      self.instruments[ticker]['target'] = pd.cut(self.instruments[ticker]['target'], bins, labels=labels)

      df = pd.concat(
        [
          df,
          self.instruments[ticker]
        ]
      )

    if drop_nulls:
      df = df.dropna()

    df['Date'] = pd.to_datetime(df['Date'], format=self.date_format)
    df = df.sort_values(by='Date')

    print(f'df value_counts {df["target"].value_counts()}')

    path = os.path.join(symbols_path, 'dataset.csv')

    if save:
      df.to_csv(path, index=False)
    
    return df


  def trading_bot_workflow(
      self, 
      actual_date:datetime, 
      df:pd.DataFrame, 
      train_period:int, 
      train_window:int, 
      period_forward_target:int
    ) -> None:
    """Flujo de trabajo del bot de trading y aprendizaje automático.

    Args:
        actual_date: Fecha actual del proceso de trading.
        df: DataFrame con los datos de mercado.
        train_period (int): frecuencia de reentrenamiento de el modelo de aprendizaje automático.
        train_window: Ventana de entrenamiento.
        period_forward_target (int): Periodo de tiempo hacia adelante para calcular el objetivo de predicción.
    """
    # ultimo periodo disponible en la realidad
    date_to = actual_date - timedelta(hours=period_forward_target + 1)
    # de ese momento, n horas hacia atras
    date_from = date_to - train_window

    actual_date_str = actual_date.strftime(self.date_format)

    today_market_data = df[df.Date == actual_date_str].copy()

    print('='*16, f'Fecha actual: {actual_date}', '='*16)
    print('Datos para la fecha actual', today_market_data[['Date', 'ticker', 'target']])

    # Si no tiene datos para entrenar en esa ventana que pase al siguiente periodo
    market_data_window = df[(df.Date >= date_from) & (df.Date < date_to)].dropna()
    
    if market_data_window.shape[0] < 70:
      print(f'No existen datos para el intervalo {date_from}-{actual_date}, se procedera con el siguiente')
      return
    
    if self.ml_agent is not None:
      
      # si nunca entreno o si ya pasaron los dias
      if (self.ml_agent.days_from_train is None or self.ml_agent.days_from_train >= train_period):

        print(f'Se entrenaran con {market_data_window.shape[0]} registros')
        print(f'Value counts de ticker: {market_data_window.ticker.value_counts()}')

        self.ml_agent.train(
            x_train = market_data_window.drop(columns=['target', 'Date', 'ticker']),
            x_test = today_market_data.drop(columns=['target', 'Date', 'ticker']),
            y_train = market_data_window.target,
            y_test = today_market_data.target,
            date_train=actual_date,
            verbose=True,
        )

        self.ml_agent.days_from_train = 1
        print('Entrenamiento terminado! :)')
      else:
        self.ml_agent.days_from_train += 1

      pred = self.ml_agent.predict_proba(today_market_data.drop(columns=['target', 'Date', 'ticker']))
      
      pred_per_ticker = pd.DataFrame({'ticker':today_market_data.ticker, 'pred':pred})
      print(f'Prediccion: {pred_per_ticker}')

      today_market_data.loc[:, 'pred'] = pred
    
    for _, stock in today_market_data.iterrows():
      if self.ml_agent is not None:
        self.ml_agent.save_predictions(
          stock.Date,
          stock.ticker, 
          stock.target, 
          stock.pred
        )

      result = self.trader.take_operation_decision(
        actual_market_data=stock.drop(columns=['target']),
        actual_date=actual_date
      )

      # write_in_logs(
      #     path=os.path.join(self.save_orders_path, 'orders.txt'), 
      #     time=actual_date, 
      #     comment="Close position", 
      #     content=str(result._asdict())
      # )

      