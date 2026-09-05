from typing import Any

from sklearn.base import BaseEstimator

from finai.domain.modeling.enums import ModelType
from finai.infrastructure.modeling.trainers.linear_regression_trainer import (
    create_linear_regression_model,
)
from finai.infrastructure.modeling.trainers.logistic_regression_trainer import (
    create_logistic_regression_model,
)
from finai.infrastructure.modeling.trainers.random_forest_trainer import (
    create_random_forest_classifier,
    create_random_forest_regressor,
)


def create_model(
    *,
    model_type: ModelType,
    parameters: dict[str, Any],
    random_seed: int,
) -> BaseEstimator:
    if model_type == ModelType.LOGISTIC_REGRESSION:
        return create_logistic_regression_model(
            parameters=parameters,
            random_seed=random_seed,
        )

    if model_type == ModelType.RANDOM_FOREST_CLASSIFIER:
        return create_random_forest_classifier(
            parameters=parameters,
            random_seed=random_seed,
        )

    if model_type == ModelType.LINEAR_REGRESSION:
        return create_linear_regression_model(
            parameters=parameters,
        )

    if model_type == ModelType.RANDOM_FOREST_REGRESSOR:
        return create_random_forest_regressor(
            parameters=parameters,
            random_seed=random_seed,
        )

    raise ValueError(f"Unsupported model type: {model_type}")
