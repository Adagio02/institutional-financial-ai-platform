import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from finai.infrastructure.prediction.explainer import (
    calculate_feature_contributions,
)


def test_linear_model_explanation() -> None:
    training_features = pd.DataFrame(
        {
            "feature_one": [
                1.0,
                2.0,
                3.0,
                4.0,
            ],
            "feature_two": [
                4.0,
                3.0,
                2.0,
                1.0,
            ],
        }
    )

    targets = [
        1.0,
        2.0,
        3.0,
        4.0,
    ]

    model = Pipeline(
        [
            (
                "scaler",
                StandardScaler(),
            ),
            (
                "model",
                LinearRegression(),
            ),
        ]
    )

    model.fit(
        training_features,
        targets,
    )

    feature_frame = training_features.tail(1)

    (
        baseline,
        contributions,
        metadata,
    ) = calculate_feature_contributions(
        model=model,
        feature_frame=feature_frame,
    )

    assert baseline is not None

    assert set(contributions) == {
        "feature_one",
        "feature_two",
    }

    assert metadata["method"] == "linear_coefficient_contribution"

    assert all(isinstance(value, float) for value in contributions.values())
