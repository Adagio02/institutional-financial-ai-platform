from __future__ import annotations

from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge, SGDRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def create_v48_models():
    return {
        "v48_ridge_ranker": Pipeline([
            ("scale", StandardScaler()),
            ("model", Ridge(alpha=10.0)),
        ]),
        "v48_sgd_huber_ranker": Pipeline([
            ("scale", StandardScaler()),
            ("model", SGDRegressor(
                loss="huber",
                penalty="l2",
                alpha=1e-5,
                max_iter=2000,
                tol=1e-4,
                early_stopping=True,
                validation_fraction=0.10,
                n_iter_no_change=10,
                random_state=42,
            )),
        ]),
        "v48_hist_gradient_boosting_ranker": HistGradientBoostingRegressor(
            learning_rate=0.05,
            max_iter=140,
            max_leaf_nodes=31,
            min_samples_leaf=100,
            l2_regularization=1.0,
            random_state=42,
        ),
    }
