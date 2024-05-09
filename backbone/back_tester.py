import os
from datetime import timedelta
import pandas as pd
from backbone.machine_learning_agent import MachineLearningAgent
from backbone.trading_agent import TradingAgent
import numpy as np
import MetaTrader5 as mt5
import pytz
from datetime import datetime

class BackTester():
  """Simulador de Backtesting para evaluar estrategias de trading."""

  def __init__(self, tickers:list, ml_agent:MachineLearningAgent, trading_agent:TradingAgent):
    """Inicializa el Simulador de Backtesting.

    Args:
        tickers (list): Lista de tickers financieros.
        ml_agent (MachineLearningAgent): Agente de Aprendizaje Automático.
        trading_agent (TradingAgent): Agente de Trading.
    """
    self.ml_agent = ml_agent
    self.trading_agent = trading_agent
    self.tickers = tickers
    self.instruments = {}

  def create_dataset(self, symbols_path:str, period:int, date_from:str, date_to:str):
    """Crea el conjunto de datos para el backtesting.

    Args:
        data_path (str): Ruta donde se guardarán los datos.
        days_back (int): Número de días para calcular el objetivo de predicción.
        period (int): Período de tiempo para obtener datos históricos.
        limit_date_train (str): Fecha límite para el conjunto de entrenamiento.
    """

    for ticker in self.tickers:
      try:
        print(f'Intentando levantar el dataset {ticker}')
        self.instruments[ticker] = pd.read_csv(os.path.join(symbols_path, f'{ticker}.csv'))

      except FileNotFoundError:

        # display data on the MetaTrader 5 package
        print(f'No se encontro el dataset {ticker}. Llamando a metatrader')
        print("MetaTrader5 package author: ", mt5.__author__)
        print("MetaTrader5 package version: ", mt5.__version__)
        
        # establish connection to MetaTrader 5 terminal
        if not mt5.initialize():
            raise Exception("initialize() failed, error code =",mt5.last_error())
        
        # set time zone to UTC
        timezone = pytz.timezone("Etc/UTC")

        # create 'datetime' objects in UTC time zone to avoid the implementation of a local time zone offset
        date_format = '%Y-%m-%d %H:%M:%S'
        utc_from = datetime.strptime(date_from, date_format).replace(tzinfo=timezone)
        utc_to = datetime.strptime(date_to, date_format).replace(tzinfo=timezone)

        # get bars from USDJPY M5 within the interval of 2020.01.10 00:00 - 2020.01.11 13:00 in UTC time zone
        rates = mt5.copy_rates_range(ticker, mt5.TIMEFRAME_H1, utc_from, utc_to)
        
        # shut down connection to the MetaTrader 5 terminal
        mt5.shutdown()
        # display each element of obtained data in a new line
        
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

        
      self.instruments[ticker]['Date'] = pd.to_datetime(self.instruments[ticker]['Date'])
      print(self.instruments[ticker].sample(5))

      print('='*16, 'calculando indicadores', '='*16)

      self.instruments[ticker] = self.trading_agent.calculate_indicators(self.instruments[ticker])
      
      self.instruments[ticker].to_csv(
        os.path.join(symbols_path, f'{ticker}.csv'), 
        index=False
      )
      
      print(f'Dataset {ticker} levantado y guardado correctamente')

  def start(
      self, 
      symbols_path:str, 
      train_window:int, 
      train_period:int, 
      mode, 
      limit_date_train, 
      results_path, 
      period_forward_target
  ):
    """Inicia el proceso de backtesting.

    Args:
        data_path (str): Ruta donde se encuentran los datos de entrada.
        train_window (int): Ventana de entrenamiento para el modelo.
        train_period (int): Período de entrenamiento para el modelo.
        results_path (str): Ruta donde se guardarán los resultados del backtesting.
    """
    df = pd.DataFrame()

    for ticker in self.tickers:
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

    df = df.dropna()
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values(by='Date')

    print(f'df value_counts {df["target"].value_counts()}')

    path = os.path.join(symbols_path, 'dataset.csv')
    df.to_csv(path, index=False)

    train_window = timedelta(hours=train_window)

    periods = df.Date.unique()
    days_from_train = None

    print('='*16, 'Iniciando backtesting', '='*16)

    start_date = periods[0] + train_window if mode=='train' else limit_date_train
    periods = periods[periods > start_date]

    for period in periods:
      actual_date = period

      # ultimo periodo disponible en la realidad
      date_to = actual_date - timedelta(hours=period_forward_target+1)
      
      # de ese momento, n horas hacia atras
      date_from = date_to - train_window

      today_market_data = df[df.Date == actual_date].copy()

      print('='*16, f'Fecha actual: {actual_date}', '='*16)
      print('Datos para la fecha actual', today_market_data[['Date', 'ticker', 'target']])

      today_market_data.loc[:, 'pred'] = np.nan

      # Si no tiene datos para entrenar en esa ventana que pase al siguiente periodo
      market_data_window = df[(df.Date >= date_from) & (df.Date < date_to)]
      
      if market_data_window.shape[0] < 70:
        print(f'No existen datos para el intervalo {date_from}-{actual_date}, se procedera con el siguiente')
        continue
      
      if self.ml_agent is not None:
        
        # si nunca entreno o si ya pasaron los dias
        if (days_from_train is None or days_from_train >= train_period):

          print(f'Se entrenaran con {market_data_window.shape[0]} registros')
          print(f'Value counts de ticker: {market_data_window.ticker.value_counts()}')

          self.ml_agent.train(
              x_train = market_data_window.drop(columns=['target', 'Date', 'ticker']),
              x_test = today_market_data.drop(columns=['target', 'Date', 'ticker']),
              y_train = market_data_window.target,
              y_test = today_market_data.target,
              date_train=actual_date.strftime('%Y-%m-%d %H:%M:%S'),
              verbose=True
          )

          days_from_train = 0
          print('Entrenamiento terminado! :)')
        else:
          days_from_train += 1

        pred = self.ml_agent.predict_proba(today_market_data.drop(columns=['target', 'Date', 'ticker']))
        print(f'Prediccion: {pred}')
        today_market_data.loc[:, 'pred'] = pred
      
      for _, stock in today_market_data.iterrows():
        if self.ml_agent is not None:
          self.ml_agent.save_predictions(
            stock.Date,
            stock.ticker, 
            stock.target, 
            stock.pred
          )

        self.trading_agent.take_operation_decision(
          actual_market_data=stock.drop(columns=['target']),
          actual_date=actual_date
        )

    os.mkdir(results_path)
    # Guarda resultados
    if self.ml_agent is not None:
      stock_predictions, stock_true_values, train_results_df = self.ml_agent.get_results()
      stock_predictions.to_csv(os.path.join(results_path, 'preds.csv'), index=False)
      stock_true_values.to_csv(os.path.join(results_path, 'truevals.csv'), index=False)
      train_results_df.to_csv(os.path.join(results_path, 'trainres.csv'), index=False)

    orders, wallet = self.trading_agent.get_orders()
    orders.to_csv(os.path.join(results_path, 'orders.csv'), index=False)
    wallet.to_csv(os.path.join(results_path, 'wallet.csv'), index=False)
