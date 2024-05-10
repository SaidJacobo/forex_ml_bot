import os
from datetime import timedelta
from backbone.machine_learning_agent import MachineLearningAgent
from backbone.trading_agent import TradingAgent
from backbone.metabot import ABCMetaBot

class BackTester(ABCMetaBot):
  """Simulador de Backtesting para evaluar estrategias de trading."""

  def __init__(self, tickers:list, ml_agent:MachineLearningAgent, trading_agent:TradingAgent):
    """Inicializa el Simulador de Backtesting.

    Args:
        tickers (list): Lista de tickers financieros.
        ml_agent (MachineLearningAgent): Agente de Aprendizaje Automático.
        trading_agent (TradingAgent): Agente de Trading.
    """
    super().__init__(tickers, ml_agent, trading_agent)

  def save_results(self, results_path):
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
    df = self.generate_dataset(
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

      self.trading_bot_workflow(actual_date, df, train_period, train_window, period_forward_target)

    self.save_results(results_path)
