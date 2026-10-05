from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import RobustScaler

from .validation import safe_rank_ic


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


def fit_predict_ranked(
    train: pd.DataFrame,
    test: pd.DataFrame,
    features: list[str],
    seed: int,
    calibration_periods: int = 126,
) -> pd.DataFrame:
    """Fit cross-sectional rank targets and calibrate direction on training data only."""
    labeled = train.dropna(subset=["forward_return"]).copy()
    labeled["rank_target"] = (
        labeled.groupby("timestamp", observed=True)["forward_return"].rank(pct=True) - 0.5
    )
    dates = sorted(labeled.timestamp.unique())
    calibration_dates = dates[-calibration_periods:]
    fit_dates = dates[:-calibration_periods]
    if len(fit_dates) < 252:
        raise ValueError("Insufficient pre-calibration training history")
    fit_frame = labeled[labeled.timestamp.isin(fit_dates)]
    calibration = labeled[labeled.timestamp.isin(calibration_dates)]
    carry = ["timestamp", "symbol", "forward_return", "close"]
    carry += [c for c in ("sector", "beta", "volatility") if c in test.columns]
    output = test[carry].copy()
    for name, factory in (("elastic", _elastic), ("tree", _tree)):
        calibration_model = factory(seed)
        calibration_model.fit(fit_frame[features], fit_frame.rank_target)
        calibration = calibration.copy()
        calibration[name] = pd.Series(
            calibration_model.predict(calibration[features]), index=calibration.index
        ).groupby(calibration.timestamp).rank(pct=True) - 0.5
        daily_ic = calibration.groupby("timestamp", observed=True).apply(
            lambda section: safe_rank_ic(section, name), include_groups=False
        ).dropna()
        calibration_ic = float(daily_ic.mean()) if len(daily_ic) else 0.0
        model = factory(seed)
        model.fit(labeled[features], labeled.rank_target)
        output[name] = pd.Series(
            model.predict(test[features]), index=test.index
        ).groupby(test.timestamp).rank(pct=True) - 0.5
        output[f"{name}_calibration_ic"] = calibration_ic
    return output


def fit_predict_residual_ranked(
    train: pd.DataFrame,
    test: pd.DataFrame,
    features: list[str],
    seed: int,
    calibration_periods: int = 126,
) -> pd.DataFrame:
    target = "forward_residual_return"
    labeled = train.dropna(subset=[target]).copy()
    labeled["rank_target"] = labeled.groupby("timestamp", observed=True)[target].rank(pct=True) - .5
    dates = sorted(labeled.timestamp.unique())
    calibration_dates, fit_dates = dates[-calibration_periods:], dates[:-calibration_periods]
    if len(fit_dates) < 252: raise ValueError("Insufficient pre-calibration history")
    fit_frame = labeled[labeled.timestamp.isin(fit_dates)]
    calibration = labeled[labeled.timestamp.isin(calibration_dates)].copy()
    carry = ["timestamp","symbol","forward_return",target,"close","sector","beta","volatility"]
    output = test[[c for c in carry if c in test.columns]].copy()
    for name, factory in (("elastic", _elastic), ("tree", _tree)):
        calibration_model = factory(seed)
        calibration_model.fit(fit_frame[features], fit_frame.rank_target)
        calibration[name] = pd.Series(
            calibration_model.predict(calibration[features]), index=calibration.index
        ).groupby(calibration.timestamp).rank(pct=True) - .5
        def residual_ic(section):
            pair = section[[name, target]].dropna()
            if len(pair) < 4 or pair[name].nunique() < 2 or pair[target].nunique() < 2:
                return np.nan
            return float(pair[name].corr(pair[target], method="spearman"))
        daily = calibration.groupby("timestamp", observed=True).apply(
            residual_ic, include_groups=False
        ).dropna()
        model = factory(seed); model.fit(labeled[features], labeled.rank_target)
        output[name] = pd.Series(
            model.predict(test[features]), index=test.index
        ).groupby(test.timestamp).rank(pct=True) - .5
        output[f"{name}_calibration_ic"] = float(daily.mean()) if len(daily) else 0.
    return output
