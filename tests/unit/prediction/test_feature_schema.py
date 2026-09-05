import pandas as pd
import pytest

from finai.domain.prediction.validation import (
    validate_feature_schema,
    validate_prediction_frame,
)


def test_feature_schema_accepts_exact_match() -> None:
    frame = pd.DataFrame(
        [
            {
                "simple_return": 0.01,
                "momentum_10": 2.5,
            }
        ],
        columns=[
            "simple_return",
            "momentum_10",
        ],
    )

    validate_feature_schema(
        frame=frame,
        expected_columns=[
            "simple_return",
            "momentum_10",
        ],
    )


def test_feature_schema_rejects_wrong_order() -> None:
    frame = pd.DataFrame(
        [
            {
                "momentum_10": 2.5,
                "simple_return": 0.01,
            }
        ],
        columns=[
            "momentum_10",
            "simple_return",
        ],
    )

    with pytest.raises(
        ValueError,
        match="order",
    ):
        validate_feature_schema(
            frame=frame,
            expected_columns=[
                "simple_return",
                "momentum_10",
            ],
        )


def test_prediction_frame_rejects_multiple_rows() -> None:
    frame = pd.DataFrame(
        {
            "simple_return": [
                0.01,
                0.02,
            ]
        }
    )

    with pytest.raises(
        ValueError,
        match="exactly one row",
    ):
        validate_prediction_frame(frame)
