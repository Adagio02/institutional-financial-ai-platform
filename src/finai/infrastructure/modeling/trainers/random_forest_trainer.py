from typing import Any

from sklearn.ensemble import (
    RandomForestClassifier,
    RandomForestRegressor,
)


def create_random_forest_classifier(
    *,
    parameters: dict[str, Any],
    random_seed: int,
) -> RandomForestClassifier:
    allowed_parameters = {
        "n_estimators",
        "max_depth",
        "min_samples_split",
        "min_samples_leaf",
        "max_features",
        "class_weight",
        "n_jobs",
    }

    filtered_parameters = {
        key: value for key, value in parameters.items() if key in allowed_parameters
    }

    filtered_parameters.setdefault(
        "n_estimators",
        200,
    )

    filtered_parameters.setdefault(
        "n_jobs",
        -1,
    )

    return RandomForestClassifier(
        random_state=random_seed,
        **filtered_parameters,
    )


def create_random_forest_regressor(
    *,
    parameters: dict[str, Any],
    random_seed: int,
) -> RandomForestRegressor:
    allowed_parameters = {
        "n_estimators",
        "max_depth",
        "min_samples_split",
        "min_samples_leaf",
        "max_features",
        "n_jobs",
    }

    filtered_parameters = {
        key: value for key, value in parameters.items() if key in allowed_parameters
    }

    filtered_parameters.setdefault(
        "n_estimators",
        200,
    )

    filtered_parameters.setdefault(
        "n_jobs",
        -1,
    )

    return RandomForestRegressor(
        random_state=random_seed,
        **filtered_parameters,
    )
