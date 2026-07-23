from __future__ import annotations
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def build_model(alpha: float = 0.001, l1_ratio: float = 0.5) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("model", ElasticNet(alpha=alpha, l1_ratio=l1_ratio, max_iter=10000)),
        ]
    )


def fit_model(frame: pd.DataFrame, features: list[str], target: str) -> Pipeline:
    model = build_model()
    model.fit(frame[features], frame[target])
    return model
