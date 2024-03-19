import os
from datetime import timedelta
import pandas as pd


class BackTester():
  def __init__(self, stocks, ml_agent, trading_agent):
    self.ml_agent = ml_agent
    self.trading_agent = trading_agent
    self.stocks = stocks
  
  def start(self, train_window, train_period, results_path):
    print('='*16, 'calculando indicadores', '='*16)

    df = pd.DataFrame()
    for ticker, stock in self.stocks.items():
      self.stocks[ticker] = self.trading_agent.calculate_indicators(stock)
      self.stocks[ticker]['ticker'] = ticker

      df = pd.concat(
        [
          df,
          self.stocks[ticker]
        ]
      )

    df = df.sort_values(by='Date')
    df.to_csv('./data/df_features.csv', index=False)

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
          stock.ticker, 
          stock.target, 
          stock.pred
        )

        self.trading_agent.take_operation_decision(
          actual_market_data=stock.drop(columns=['target']),
          actual_date=actual_date
        )
      
    buys, sells, wallet = self.trading_agent.get_orders()
    ml_results = self.ml_agent.get_results()

    path = os.path.join('data', results_path)
    os.mkdir(path)

    # Guarda resultados
    buys.to_csv(os.path.join(path, 'buys.csv'), index=False)
    sells.to_csv(os.path.join(path, 'sells.csv'), index=False)
    wallet.to_csv(os.path.join(path, 'wallet.csv'), index=False)
    ml_results.to_csv(os.path.join(path, 'ml_results.csv'), index=False)


