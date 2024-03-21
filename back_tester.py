import os
from datetime import timedelta
import pandas as pd
import yfinance as yf


class BackTester():
  def __init__(self, tickers, ml_agent, trading_agent):
    self.ml_agent = ml_agent
    self.trading_agent = trading_agent
    self.tickers = tickers
    self.stocks = {}

  def create_dataset(self, data_path, days_back, period, limit_date_train):
    df = pd.DataFrame()

    for ticker in self.tickers:
      try:
        print(f'Intentando levantar el dataset {ticker}')
        self.stocks[ticker] = pd.read_csv(f'./data/{ticker}.csv')

      except FileNotFoundError:
        print(f'No se encontro el Dataset {ticker}, llamando a yfinance')

        self.stocks[ticker] = yf.Ticker(ticker).history(period=period).reset_index()
        self.stocks[ticker]['Date'] = self.stocks[ticker]['Date'].dt.date
        self.stocks[ticker].to_csv(f'./data/{ticker}.csv', index=False)

        print('Dataset levantado y guardado correctamente')
        
      self.stocks[ticker]['Date'] = pd.to_datetime(self.stocks[ticker]['Date'])
      print(self.stocks[ticker].sample(5))

      print('Creando target')

      self.stocks[ticker]['target'] = ((self.stocks[ticker]['Close'].shift(-days_back) - self.stocks[ticker]['Close']) / self.stocks[ticker]['Close']) * 100
      self.stocks[ticker]['target'] = self.stocks[ticker]['target'].round(0)

      bins = [-25, 0, 25]
      labels = [0, 1]

      self.stocks[ticker]['target'] = pd.cut(self.stocks[ticker]['target'], bins, labels=labels)

      print('='*16, 'calculando indicadores', '='*16)

      self.stocks[ticker] = self.trading_agent.calculate_indicators(self.stocks[ticker])
      self.stocks[ticker]['ticker'] = ticker

      df = pd.concat(
        [
          df,
          self.stocks[ticker]
        ]
      )

    df = df.sort_values(by='Date')
    
    df_train = df[df.Date <= limit_date_train]
    df_test = df[df.Date > limit_date_train]

    df_train.to_csv(os.path.join(data_path, 'train.csv'), index=False)
    df_test.to_csv(os.path.join(data_path, 'test.csv'), index=False)


  def start(self, data_path, train_window, train_period, results_path):
    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])

    train_window = timedelta(days=train_window)

    dates = df.Date.unique()
    days_from_train = None

    print('='*16, 'Iniciando backtesting', '='*16)

    start_date = dates[0] + train_window
    dates = dates[dates > start_date]

    for date in dates:
      actual_date = date
      date_from = date - train_window
      
      actual_market_data = df[df.Date == actual_date]

      print('='*16, f'Fecha actual: {actual_date}', '='*16)
      print('Datos para la fecha actual', actual_market_data[['Date', 'ticker', 'target']])

      # si nunca entreno o si ya pasaron los dias suficientes entrena
      if days_from_train is None or days_from_train >= train_period:
        market_data_window = df[(df.Date >= date_from) & (df.Date < actual_date)]

        print(f'Se entrenaran con {market_data_window.shape[0]} registros')
        print(f'Value counts de ticker: {market_data_window.ticker.value_counts()}')

        self.ml_agent.train(
            x_train = market_data_window.drop(columns=['target', 'Date', 'ticker']),
            x_test = actual_market_data.drop(columns=['target', 'Date', 'ticker']),
            y_train = market_data_window.target,
            y_test = actual_market_data.target,
            verbose=True
        )

        days_from_train = 0
        print('Entrenamiento terminado! :)')
      else:
        days_from_train += 1

      pred = self.ml_agent.predict_proba(actual_market_data.drop(columns=['target', 'Date', 'ticker']))

      print(f'Prediccion: {pred}')
      
      actual_market_data['pred'] = pred
      
      for _, stock in actual_market_data.iterrows():
      
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
      
    buys, sells, wallet = self.trading_agent.get_orders()
    stock_predictions, stock_true_values = self.ml_agent.get_results()

    path = os.path.join('data', results_path)
    os.mkdir(path)

    # Guarda resultados
    buys.to_csv(os.path.join(path, 'buys.csv'), index=False)
    sells.to_csv(os.path.join(path, 'sells.csv'), index=False)
    wallet.to_csv(os.path.join(path, 'wallet.csv'), index=False)
    stock_predictions.to_csv(os.path.join(path, 'stock_predictions.csv'), index=False)
    stock_true_values.to_csv(os.path.join(path, 'stock_true_values.csv'), index=False)


