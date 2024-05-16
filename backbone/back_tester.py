import os
from datetime import timedelta
from backbone.botardo import Botardo

class BackTester():
  """Simulador de Backtesting para evaluar estrategias de trading."""

  def __init__(self, botardo: Botardo):
    """Inicializa el Simulador de Backtesting.

    Args:
        tickers (list): Lista de tickers financieros.
        ml_agent (MachineLearningAgent): Agente de Aprendizaje Automático.
        trading_agent (Trader): Agente de Trading.
    """
    self.botardo = botardo

  def save_results(self, results_path:str) -> None:
    os.mkdir(results_path)
    # Guarda resultados
    if self.botardo.ml_agent is not None:
      stock_predictions, stock_true_values, train_results_df, best_params = self.botardo.ml_agent.get_results()
      stock_predictions.to_csv(os.path.join(results_path, 'preds.csv'), index=False)
      stock_true_values.to_csv(os.path.join(results_path, 'truevals.csv'), index=False)
      train_results_df.to_csv(os.path.join(results_path, 'trainres.csv'), index=False)

      # Guardar los mejores parámetros en un archivo de texto
      with open(os.path.join(results_path, 'params.txt'), 'w') as file:
        for key, value in best_params.items():
            file.write(f'{key}: {value}\n')

    orders, wallet = self.botardo.trader.get_orders()
    orders.to_csv(os.path.join(results_path, 'orders.csv'), index=False)
    wallet.to_csv(os.path.join(results_path, 'wallet.csv'), index=False)

  def start(
      self, 
      symbols_path:str, 
      train_window:int, 
      train_period:int, 
      mode:str, 
      limit_date_train:str, 
      results_path:str, 
      period_forward_target:int
  ) -> None:
    """Inicia el proceso de backtesting.

    Args:
        data_path (str): Ruta donde se encuentran los datos de entrada.
        train_window (int): Ventana de entrenamiento para el modelo.
        train_period (int): Período de entrenamiento para el modelo.
        results_path (str): Ruta donde se guardarán los resultados del backtesting.
    """
    df = self.botardo.generate_dataset(
      symbols_path=symbols_path, 
      period_forward_target=period_forward_target, 
      # Levanta los simbolos que guardo en la carpeta de simbolos, deberia funcionar tambien con lo que
      # tiene en memoria pisandolo, pero hay que testearlo.
      load_symbols_from_disk=True,
      drop_nulls=True
    )

    train_window = timedelta(hours=train_window)

    periods = df.Date.unique()

    print('='*16, 'Iniciando backtesting', '='*16)

    start_date = periods[0] + train_window if mode=='train' else limit_date_train
    periods = periods[periods > start_date]

    for period in periods:
      actual_date = period

      self.botardo.trading_bot_workflow(
        actual_date, 
        df, 
        train_period, 
        train_window, 
        period_forward_target, 
      )

    self.save_results(results_path)
