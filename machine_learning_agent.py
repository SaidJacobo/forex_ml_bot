import pandas as pd
from sklearn.metrics import classification_report
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.compose import ColumnTransformer
from sklearn.metrics import fbeta_score, make_scorer, classification_report
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import RobustScaler

class MachineLearningAgent():

  def __init__(self, model, param_grid, only_one_tunning):
    self.model = model
    self.param_grid = param_grid
    self.pipeline = None
    self.only_one_tunning = only_one_tunning
    self.tunning = True
    self.y_test = []
    self.y_pred = []

  def predict(self, x):
    pred = self.pipeline.predict(x)
    return pred

  def predict_proba(self, x):
    proba = self.pipeline.predict_proba(x)

    try:
      pred = proba[:,1] # si el array tiene dos valores agarro el segundo
    except:
      pred = proba[:,0] # si tiene uno solo es porque esta super seguro de una de las dos clases, y agarro ese valor
      
    return pred

  def train(self, x_train, x_test, y_train, y_test, verbose=False):
    
    if self.tunning:
      print('Starting tunning')
      columns_to_scale = x_train.columns
      # Definir el transformador para las columnas que se deben escalar
      scaler = ColumnTransformer(
          transformers=[
              ('scaler', RobustScaler(), columns_to_scale)
          ],
          remainder='passthrough'  # Las demás columnas se mantienen sin cambios
      )

      pipe = Pipeline([
          ('scaler', scaler),
          ('model', self.model)
      ])

      n_splits = 3
      stratified_kfold = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

      search = GridSearchCV(
          pipe,
          self.param_grid,
          n_jobs=-1,
          cv=stratified_kfold,
          scoring=make_scorer(fbeta_score, beta=0.2)
      )

      # Entrenar
      search.fit(x_train, y_train)

      if verbose:
        print("Best parameter (CV score=%0.3f):" % search.best_score_)

        print(f'Best params: {search.best_params_}')

      # Obtengo el best estimator
      self.pipeline = search.best_estimator_

      if self.only_one_tunning:
        self.tunning = False

    else:
      print('Starting train')
      print(f'y_train value_counts: {y_train.value_counts()}')
      
      try:
        self.pipeline.fit(x_train, y_train)

        # Prediccion de train    
        if verbose:
          y_pred = self.predict(x_train)
          print('='*16, 'classification_report_train', '='*16)
          class_report = classification_report(y_train, y_pred)
          print(class_report)

        # Prediccion de test
        y_pred = self.predict_proba(x_test)

      except:
        print('Entrenamiento cancelado')



  def save_predictions(self, y_true, y_pred):
    self.y_test.append(y_true)
    self.y_pred += list(y_pred)

  def get_results(self):
    results_df = pd.DataFrame(
      {
        'y_true': self.y_test, 
        'y_pred': self.y_pred
       }
    )
    
    return results_df