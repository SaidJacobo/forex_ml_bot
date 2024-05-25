import numpy as np
from sklearn.linear_model import LogisticRegression
from backbone.probability_transformer import ProbabilityTransformer 
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.metrics import f1_score, make_scorer, precision_score, recall_score
from sklearn.preprocessing import StandardScaler
from backbone.utils import load_function
from typing import Tuple

class MachineLearningAgent():
  """Agente de Aprendizaje Automático para entrenar y predecir."""

  def __init__(self, tickers, model=None, pipeline=None, param_grid=None):
    """Inicializa el Agente de Aprendizaje Automático.

    Args:
        tickers (list): Lista de tickers financieros.
        model: Modelo de machine learning.
        param_grid (dict): Parámetros del modelo para búsqueda de hiperparámetros.
    """
    if model and pipeline:
      raise Exception('No puede enviarse un modelo y un pipeline')
    
    if model:
      self.model = load_function(model)
      if not param_grid:
        raise Exception('Debe adjuntarse una grilla de hiperparametros para optimizar')
      self.param_grid = param_grid
      self.pipeline = self._create_pipeline()

    elif pipeline:
      self.pipeline = pipeline


    # si llegan los parametros no tiene que tunear nada, sino armar el pipeline directamente con esos
    self.tunning = True if param_grid else False

    # Si llega la param_grid, el pipeline se arma en la funcion train, sino lo armo directamente aca con 
    # los params que corresponda
    
    self.days_from_train=None
    self.stock_predictions = {}
    self.stock_true_values = {}
    for ticker in tickers:
      self.stock_predictions[ticker] = {}
      self.stock_true_values[ticker] = {}
    
    self.train_results = {}
    self.train_results['precision'] = {}
    self.train_results['recall'] = {}
    self.train_results['f1'] = {}

    self.best_params = {}

  def _create_pipeline(self):
    scaler = StandardScaler()

    log_reg = LogisticRegression(
      multi_class='multinomial', 
      solver='lbfgs', 
      class_weight='balanced', 
      max_iter=1000,
      random_state=42
    )

    model = self.model()

    pipe = Pipeline([
        ('scaler', scaler),
        ('prob_transf', ProbabilityTransformer(model)),
        ('log_reg', log_reg)
    ])

    return pipe

  def predict(self, x):
    """Realiza predicciones.

    Args:
        x (DataFrame): Datos de entrada para realizar las predicciones.

    Returns:
        array: Predicciones del modelo.
    """
    pred = self.pipeline.predict(x)
    return pred

  def predict_proba(self, x):
    """Realiza predicciones de probabilidad.

    Args:
        x (DataFrame): Datos de entrada para realizar las predicciones.

    Returns:
        array: Predicciones de probabilidad del modelo.
    """
    predictions = self.pipeline.predict_proba(x)

    # Obtener la probabilidad más grande para cada sub-array
    max_probabilities = np.max(predictions, axis=1)

    # Obtener los índices de la probabilidad más grande para cada sub-array
    max_indices = np.argmax(predictions, axis=1)
    
    return max_indices, max_probabilities

  def train(
      self, 
      x_train:pd.DataFrame, 
      x_test:pd.DataFrame, 
      y_train:pd.DataFrame, 
      y_test:pd.DataFrame, 
      date_train:str, 
      verbose=False,
    ) -> None:
    if self.tunning:
      n_splits = 3
      stratified_kfold = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

      search = GridSearchCV(
          self.pipeline,
          self.param_grid,
          n_jobs=-1,
          cv=stratified_kfold,
          scoring=make_scorer(f1_score, average='weighted')
      )

      # Tunear hiperparametros
      search.fit(x_train, y_train)

      self.best_params = search.best_params_

      if verbose:
        print("Best parameter (CV score=%0.3f):" % search.best_score_)

        print(f'Best params: {search.best_params_}')

      # Obtengo el best estimator
      self.pipeline = search.best_estimator_
      self.tunning = False

    else:
      print('Starting train')
      print(f'y_train value_counts: {y_train.value_counts()}')
      
      self.pipeline.fit(x_train, y_train)

    train_preds = self.pipeline.predict(x_train)
    train_target = y_train

    precision = precision_score(train_target, train_preds, average='macro')
    recall = recall_score(train_target, train_preds, average='macro')
    f1 = f1_score(train_target, train_preds, average='macro')

    self.train_results['precision'][date_train] = precision
    self.train_results['recall'][date_train] = recall
    self.train_results['f1'][date_train] = f1

    if verbose:
      print('train precision: ', precision)
      print('train recall: ', recall)
      print('train f1: ', f1)


  def save_predictions(
      self, 
      date:str, 
      ticker:str, 
      y_true:pd.DataFrame, 
      pred_label:pd.DataFrame, 
    ) -> None:
    """Guarda las predicciones del modelo.

    Args:
        date (datetime): Fecha de las predicciones.
        ticker (str): Ticker financiero.
        y_true (array): Valores verdaderos.
        y_pred (array): Valores predichos.
    """
    self.stock_predictions[ticker][date] = pred_label
    self.stock_true_values[ticker][date] = y_true

  def get_results(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Obtiene los resultados del modelo.

    Returns:
        DataFrame: Predicciones del modelo.
        DataFrame: Valores verdaderos.
    """
    stock_predictions_df = pd.DataFrame(self.stock_predictions)
    stock_true_values_df = pd.DataFrame(self.stock_true_values)
    stock_train_results_df = pd.DataFrame(self.train_results)

    stock_predictions_df = stock_predictions_df.reset_index().rename(columns={'index':'fecha'})
    stock_true_values_df = stock_true_values_df.reset_index().rename(columns={'index':'fecha'})

    return stock_predictions_df, stock_true_values_df, stock_train_results_df