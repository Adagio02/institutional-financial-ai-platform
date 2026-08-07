from collections.abc import Sequence

import pandas as pd


def validate_feature_schema(
    *,
    frame: pd.DataFrame,
    expected_columns: Sequence[str],
) -> None:
    expected = list(expected_columns)
    actual = list(frame.columns)

    missing = sorted(set(expected) - set(actual))
    unexpected = sorted(set(actual) - set(expected))

    if missing:
        raise ValueError("Prediction input is missing model features: " + ", ".join(missing))

    if unexpected:
        raise ValueError("Prediction input contains unexpected features: " + ", ".join(unexpected))

    if actual != expected:
        raise ValueError("Prediction feature order does not match the model schema.")


def validate_prediction_frame(
    frame: pd.DataFrame,
) -> None:
    if frame.empty:
        raise ValueError("Prediction input cannot be empty.")

    if len(frame) != 1:
        raise ValueError("Prediction serving currently accepts exactly one row.")

    if frame.isna().any().any():
        raise ValueError("Prediction input cannot contain missing values.")
