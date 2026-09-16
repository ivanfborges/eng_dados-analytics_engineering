"""Fold-local estimators for the frozen rio-model-v1 candidates."""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin, RegressorMixin
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer, MissingIndicator
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.preprocessing import OneHotEncoder, StandardScaler


class SemanticCleaner(TransformerMixin, BaseEstimator):
    def __init__(self, numeric, categorical):
        self.numeric = numeric
        self.categorical = categorical

    def fit(self, X, y=None):
        self.transform(X)
        return self

    def transform(self, X):
        result = pd.DataFrame(index=X.index)
        for field in self.numeric:
            values = pd.to_numeric(X[field], errors='coerce').astype(float)
            valid = np.isfinite(values)
            if field in {'latitude', 'longitude'}:
                valid &= values.abs() <= (90 if field == 'latitude' else 180)
            else:
                valid &= values >= (1 if field in {'accommodates','minimum_nights'} else 0)
                if field != 'bathrooms':
                    valid &= values.mod(1).eq(0)
            result[field] = values.where(valid, np.nan)
        for field in self.categorical:
            result[field] = X[field].fillna('').astype(str).replace('', '__MISSING__').astype(object)
        return result


def inverse_price(values):
    return np.maximum(0, np.expm1(values))


class MedianRegressor(RegressorMixin, BaseEstimator):
    def __init__(self, by_room=False):
        self.by_room = by_room

    def fit(self, X, y):
        frame = pd.DataFrame({'room': X.room_type.to_numpy(), 'target': np.asarray(y)})
        self.global_ = float(frame.target.median())
        self.rooms_ = frame.groupby('room').target.median().to_dict()
        return self

    def predict(self, X):
        if self.by_room:
            return X.room_type.map(self.rooms_).fillna(self.global_).to_numpy(dtype=float)
        return np.full(len(X), self.global_)


class NonnegativeHistGradientBoostingRegressor(HistGradientBoostingRegressor):
    def predict(self, X):
        return np.maximum(0, super().predict(X))


def make_model(name, protocol):
    if name in {'global_median','room_median'}:
        return MedianRegressor(by_room=name == 'room_median')
    if name not in protocol['candidate_order'][2:]:
        raise ValueError('Unknown candidate')
    numeric = list(protocol['numeric_property'])
    categorical = list(protocol['categorical_property'])
    if name.endswith('_geo'):
        numeric += ['latitude', 'longitude']
        categorical += ['neighbourhood_cleansed']
    numeric_steps = [('impute_and_flag', FeatureUnion([
        ('impute', SimpleImputer(strategy='median', keep_empty_features=True)),
        ('missing', MissingIndicator(features='all', error_on_new=False))]))]
    if name.startswith('ridge'):
        numeric_steps.append(('scale', StandardScaler()))
    preprocess = ColumnTransformer([
        ('numeric', Pipeline(numeric_steps), numeric),
        ('category', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical)],
        remainder='drop', sparse_threshold=0)
    if name.startswith('ridge'):
        estimator = Ridge(alpha=protocol['ridge']['alpha'], solver='lsqr', tol=1e-6, max_iter=10000)
    else:
        parameters = {k:v for k,v in protocol['histgb'].items() if k != 'target'}
        estimator = NonnegativeHistGradientBoostingRegressor(**parameters, categorical_features=None)
    pipeline = Pipeline([('clean', SemanticCleaner(numeric, categorical)),
                         ('preprocess', preprocess), ('estimator', estimator)])
    if name.startswith('ridge'):
        return TransformedTargetRegressor(regressor=pipeline, func=np.log1p, inverse_func=inverse_price, check_inverse=False)
    return pipeline