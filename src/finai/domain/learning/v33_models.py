from __future__ import annotations

from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import (
    LogisticRegression,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    StandardScaler,
)


def create_models() -> dict[
    str,
    object,
]:
    return {
        "logistic_regression": (
            Pipeline(
                [
                    (
                        "scale",
                        StandardScaler(),
                    ),
                    (
                        "model",
                        LogisticRegression(
                            C=0.25,
                            class_weight="balanced",
                            max_iter=2000,
                            random_state=42,
                        ),
                    ),
                ]
            )
        ),
        "random_forest": (
            RandomForestClassifier(
                n_estimators=400,
                max_depth=8,
                min_samples_leaf=20,
                max_features="sqrt",
                class_weight="balanced_subsample",
                n_jobs=-1,
                random_state=42,
            )
        ),
        "extra_trees": (
            ExtraTreesClassifier(
                n_estimators=500,
                max_depth=10,
                min_samples_leaf=15,
                max_features="sqrt",
                class_weight="balanced",
                n_jobs=-1,
                random_state=42,
            )
        ),
        "hist_gradient_boosting": (
            HistGradientBoostingClassifier(
                learning_rate=0.05,
                max_iter=250,
                max_leaf_nodes=15,
                min_samples_leaf=30,
                l2_regularization=1.0,
                random_state=42,
            )
        ),
    }