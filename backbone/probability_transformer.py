from sklearn.base import BaseEstimator, ClassifierMixin


class ProbabilityTransformer(BaseEstimator, ClassifierMixin):
    def __init__(self, model):
        self.model = model

    def fit(self, X, y=None):
        self.model.fit(X, y)
        self.classes_ = self.model.classes_  # Asegurarse de que el atributo classes_ esté presente

        return self

    def predict(self, X):
        return self.model.predict(X)

    def predict_proba(self, X):
        return self.model.predict_proba(X)