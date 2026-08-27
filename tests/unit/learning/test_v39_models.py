from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import (
    LogisticRegression,
)

from finai.domain.learning.v39_models import (
    V39RegimeEnsemble,
)


def make_features(
    rows: int = 600,
) -> pd.DataFrame:
    generator = (
        np.random.default_rng(
            42
        )
    )

    return pd.DataFrame(
        {
            "market_volatility": (
                generator.uniform(
                    0.001,
                    0.010,
                    rows,
                )
            ),
            "market_momentum": (
                generator.normal(
                    0.0,
                    0.003,
                    rows,
                )
            ),
            "return_1": (
                generator.normal(
                    0.0,
                    0.002,
                    rows,
                )
            ),
        }
    )


def make_target(
    features: pd.DataFrame,
) -> np.ndarray:
    momentum = (
        features[
            "market_momentum"
        ]
        .to_numpy()
    )

    return np.where(
        momentum > 0.001,
        1,
        np.where(
            momentum < -0.001,
            -1,
            0,
        ),
    )


def test_regime_model_fits() -> None:
    features = make_features()

    target = make_target(
        features
    )

    model = V39RegimeEnsemble(
        base_estimator=(
            LogisticRegression(
                max_iter=1000
            )
        ),
        minimum_regime_rows=100,
    )

    model.fit(
        features,
        target,
    )

    assert hasattr(
        model,
        "global_model_",
    )

    assert hasattr(
        model,
        "classes_",
    )


def test_regime_model_probabilities() -> None:
    features = make_features()

    target = make_target(
        features
    )

    model = V39RegimeEnsemble(
        base_estimator=(
            LogisticRegression(
                max_iter=1000
            )
        ),
        minimum_regime_rows=100,
    )

    model.fit(
        features,
        target,
    )

    probabilities = (
        model.predict_proba(
            features.iloc[
                :20
            ]
        )
    )

    assert probabilities.shape[
        0
    ] == 20

    assert probabilities.shape[
        1
    ] == len(
        model.classes_
    )

    assert np.allclose(
        probabilities.sum(
            axis=1
        ),
        1.0,
    )


def test_regime_model_predicts() -> None:
    features = make_features()

    target = make_target(
        features
    )

    model = V39RegimeEnsemble(
        base_estimator=(
            LogisticRegression(
                max_iter=1000
            )
        ),
        minimum_regime_rows=100,
    )

    model.fit(
        features,
        target,
    )

    predictions = model.predict(
        features.iloc[
            :10
        ]
    )

    assert len(
        predictions
    ) == 10

    assert set(
        predictions
    ).issubset(
        {-1, 0, 1}
    )