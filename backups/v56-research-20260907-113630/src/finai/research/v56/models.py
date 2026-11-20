from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import RobustScaler


def _elastic(seed: int):
    return make_pipeline(
        SimpleImputer(strategy="median"), RobustScaler(),
        ElasticNet(alpha=0.001, l1_ratio=0.15, max_iter=10000, random_state=seed),
    )


def _tree(seed: int):
    return make_pipeline(
        SimpleImputer(strategy="median"),
        HistGradientBoostingRegressor(
            learning_rate=0.035, max_iter=180, max_leaf_nodes=15,
            min_samples_leaf=30, l2_regularization=2.0, random_state=seed,
        ),
    )


def fit_predict(train: pd.DataFrame, test: pd.DataFrame, features: list[str], seed: int) -> pd.DataFrame:
    valid = train["forward_return"].notna()
    if valid.sum() < 100:
        raise ValueError("Training fold has fewer than 100 labeled rows")
    x_train, y_train = train.loc[valid, features], train.loc[valid, "forward_return"]
    carry = ["timestamp", "symbol", "forward_return", "close"]
    carry += [c for c in ("sector", "beta", "volatility") if c in test.columns]
    predictions = test[carry].copy()
    for name, model in (("elastic", _elastic(seed)), ("tree", _tree(seed))):
        model.fit(x_train, y_train)
        raw = model.predict(test[features])
        predictions[name] = pd.Series(raw, index=test.index).groupby(test["timestamp"]).rank(pct=True) - 0.5
    return predictions
