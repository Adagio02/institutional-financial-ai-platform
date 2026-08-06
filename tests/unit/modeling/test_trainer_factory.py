from sklearn.ensemble import (
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import (
    LinearRegression,
    LogisticRegression,
)

from finai.domain.modeling.enums import ModelType
from finai.infrastructure.modeling.trainer_factory import (
    create_model,
)


def test_create_logistic_regression() -> None:
    model = create_model(
        model_type=(ModelType.LOGISTIC_REGRESSION),
        parameters={},
        random_seed=42,
    )

    assert isinstance(
        model,
        LogisticRegression,
    )


def test_create_random_forest_classifier() -> None:
    model = create_model(
        model_type=(ModelType.RANDOM_FOREST_CLASSIFIER),
        parameters={"n_estimators": 10},
        random_seed=42,
    )

    assert isinstance(
        model,
        RandomForestClassifier,
    )


def test_create_linear_regression() -> None:
    model = create_model(
        model_type=(ModelType.LINEAR_REGRESSION),
        parameters={},
        random_seed=42,
    )

    assert isinstance(
        model,
        LinearRegression,
    )


def test_create_random_forest_regressor() -> None:
    model = create_model(
        model_type=(ModelType.RANDOM_FOREST_REGRESSOR),
        parameters={"n_estimators": 10},
        random_seed=42,
    )

    assert isinstance(
        model,
        RandomForestRegressor,
    )
