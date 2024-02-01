import os
from datetime import timedelta

class BackTester():
  def __init__(self, market_data, ml_agent, trading_agent):
    self.ml_agent = ml_agent
    self.trading_agent = trading_agent
    self.market_data = market_data
  
  def start(self, train_window, train_period, results_path):
    print('='*16, 'calculando indicadores', '='*16)
    self.market_data = self.trading_agent.calculate_indicators(self.market_data)
    train_window = timedelta(days=train_window)

    dates = self.market_data.Date
    days_from_train = None

    print('='*16, 'Iniciando backtesting', '='*16)

    start_date = dates.iloc[0] + train_window
    dates = dates[dates > start_date]

    for date in dates:
      actual_date = date
      date_from = date - train_window
      
      actual_market_data = self.market_data[self.market_data.Date == actual_date]

      # si nunca entreno o si ya pasaron los dias suficientes entrena
      if days_from_train is None or days_from_train >= train_period:
        market_data_window = self.market_data[
            (self.market_data.Date >= date_from) 
            & (self.market_data.Date < actual_date)
        ]

        self.ml_agent.train(
            x_train = market_data_window.drop(columns=['target', 'Date']),
            x_test = actual_market_data.drop(columns=['target', 'Date']),
            y_train = market_data_window.target,
            y_test = actual_market_data.target,
            verbose=True
        )
        days_from_train = 0
        print('train end succesfully! :)')
      else:
        days_from_train += 1

      pred = self.ml_agent.predict_proba(actual_market_data.drop(columns=['target', 'Date']))
      self.ml_agent.save_predictions(actual_market_data.iloc[0].target, pred)
      
      print(f'prediction: {pred}')
      
      self.trading_agent.take_operation_decision(
        pred=pred, 
        actual_market_data=actual_market_data.drop(columns=['target', 'Date']),
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

