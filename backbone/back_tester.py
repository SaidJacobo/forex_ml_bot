import os
from datetime import datetime, timedelta
from backbone.botardo import Botardo
import joblib


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
      train_results_df, test_results_df = self.botardo.ml_agent.get_results()
      test_results_df.to_csv(os.path.join(results_path, 'test_res.csv'), index=False)
      train_results_df.to_csv(os.path.join(results_path, 'trainres.csv'), index=False)

      pipeline = self.botardo.ml_agent.pipeline
      best_params = self.botardo.ml_agent.best_params

      with open(os.path.join(results_path, 'pipe.pkl'), 'wb') as file:
        joblib.dump(pipeline, file)

      # Guardar los mejores parámetros en un archivo de texto
      with open(os.path.join(results_path, 'params.txt'), 'w') as file:
        for key, value in best_params.items():
            file.write(f'{key}: {value}\n')

    orders, wallet = self.botardo.trader.get_orders()
    orders.to_csv(os.path.join(results_path, 'orders.csv'), index=False)
    wallet.to_csv(os.path.join(results_path, 'wallet.csv'), index=False)

  def start(
      self,
      start_date:datetime,
      symbols_path:str, 
      train_window:int, 
      train_period:int, 
      mode:str, 
      limit_date_train:str, 
      period_forward_target:int,
      undersampling:bool,
      results_path:str=None, 
      save:bool=True
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
      drop_nulls=True,
      save=True
    )

    train_window = timedelta(hours=train_window)

    dates = df.Date.unique()

    print('='*16, 'Iniciando backtesting', '='*16)

    start_date = start_date.strftime('%Y-%m-%d %H:00:00') if mode=='train' else limit_date_train
    dates = dates[dates > start_date]

    for actual_date in dates:

      self.botardo.trading_bot_workflow(
        actual_date, 
        df, 
        train_period, 
        train_window, 
        period_forward_target,
        undersampling=undersampling
      )

    if save:
      self.save_results(results_path)
