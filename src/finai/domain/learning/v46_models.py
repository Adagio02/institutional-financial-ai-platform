from __future__ import annotations

from typing import Any

from sklearn.ensemble import (
    ExtraTreesClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


MODEL_CONFIGS: dict[str, dict[str, Any]] = {
    "meta_logistic_c1": {
        "family": "logistic",
        "C": 1.0,
    },
    "meta_random_forest": {
        "family": "random_forest",
        "n_estimators": 300,
        "max_depth": 10,
        "min_samples_leaf": 20,
    },
    "meta_extra_trees": {
        "family": "extra_trees",
        "n_estimators": 300,
        "max_depth": 10,
        "min_samples_leaf": 20,
    },
}


FOCUSED_MODEL_CONFIGS: dict[str, dict[str, Any]] = {
    "meta_logistic_c0p25": {
        "family": "logistic",
        "C": 0.25,
    },
    "meta_logistic_c1": {
        "family": "logistic",
        "C": 1.0,
    },
    "meta_logistic_c4": {
        "family": "logistic",
        "C": 4.0,
    },
    "meta_random_forest_leaf10": {
        "family": "random_forest",
        "n_estimators": 400,
        "max_depth": 10,
        "min_samples_leaf": 10,
    },
    "meta_random_forest_leaf30": {
        "family": "random_forest",
        "n_estimators": 400,
        "max_depth": 10,
        "min_samples_leaf": 30,
    },
    "meta_extra_trees_leaf10": {
        "family": "extra_trees",
        "n_estimators": 400,
        "max_depth": 10,
        "min_samples_leaf": 10,
    },
    "meta_extra_trees_leaf30": {
        "family": "extra_trees",
        "n_estimators": 400,
        "max_depth": 10,
        "min_samples_leaf": 30,
    },
}


def create_meta_model(
    config: dict[str, Any],
):
    family = str(config["family"])

    if family == "logistic":
        return Pipeline(
            steps=[
                (
                    "scale",
                    StandardScaler(),
                ),
                (
                    "model",
                    LogisticRegression(
                        C=float(
                            config.get(
                                "C",
                                1.0,
                            )
                        ),
                        class_weight="balanced",
                        max_iter=2000,
                        random_state=460,
                    ),
                ),
            ]
        )

    common = {
        "n_estimators": int(
            config.get(
                "n_estimators",
                300,
            )
        ),
        "max_depth": (
            None
            if config.get(
                "max_depth"
            ) is None
            else int(
                config["max_depth"]
            )
        ),
        "min_samples_leaf": int(
            config.get(
                "min_samples_leaf",
                20,
            )
        ),
        "class_weight": "balanced",
        "n_jobs": -1,
        "random_state": 460,
    }

    if family == "random_forest":
        return RandomForestClassifier(
            **common
        )

    if family == "extra_trees":
        return ExtraTreesClassifier(
            **common
        )

    raise ValueError(
        f"Unknown meta model family: {family}"
    )
