from __future__ import annotations

from typing import Any

from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import (
    LogisticRegression,
)
from sklearn.pipeline import (
    Pipeline,
)
from sklearn.preprocessing import (
    StandardScaler,
)

from finai.domain.learning.v39_models import (
    V39RegimeEnsemble,
)


def create_v41_models(
    *,
    minimum_regime_rows: int,
) -> dict[
    str,
    V39RegimeEnsemble,
]:
    base_models: dict[
        str,
        Any,
    ] = {
        "logistic_regression": (
            Pipeline(
                steps=[
                    (
                        "scaler",
                        StandardScaler(),
                    ),
                    (
                        "classifier",
                        LogisticRegression(
                            C=0.5,
                            max_iter=2_000,
                            class_weight=(
                                "balanced"
                            ),
                            random_state=42,
                        ),
                    ),
                ]
            )
        ),
        "extra_trees": (
            ExtraTreesClassifier(
                n_estimators=300,
                max_depth=12,
                min_samples_leaf=20,
                max_features="sqrt",
                class_weight=(
                    "balanced"
                ),
                n_jobs=-1,
                random_state=42,
            )
        ),
        "random_forest": (
            RandomForestClassifier(
                n_estimators=300,
                max_depth=12,
                min_samples_leaf=20,
                max_features="sqrt",
                class_weight=(
                    "balanced_subsample"
                ),
                n_jobs=-1,
                random_state=42,
            )
        ),
        "hist_gradient_boosting": (
            HistGradientBoostingClassifier(
                learning_rate=0.05,
                max_iter=250,
                max_leaf_nodes=31,
                min_samples_leaf=30,
                l2_regularization=1.0,
                random_state=42,
            )
        ),
    }

    return {
        (
            "v41_regime_"
            + name
        ): V39RegimeEnsemble(
            base_estimator=model,
            minimum_regime_rows=(
                minimum_regime_rows
            ),
        )
        for name, model
        in base_models.items()
    }