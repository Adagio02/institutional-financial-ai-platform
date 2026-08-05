from datetime import datetime
from typing import Any


def validate_positive_window(window: int) -> int:
    if window <= 0:
        raise ValueError("Feature window must be greater than zero.")

    return window


def validate_feature_time_range(
    *,
    start_time: datetime,
    end_time: datetime,
) -> None:
    if start_time.tzinfo is None:
        raise ValueError("start_time must be timezone-aware.")

    if end_time.tzinfo is None:
        raise ValueError("end_time must be timezone-aware.")

    if start_time >= end_time:
        raise ValueError("start_time must be earlier than end_time.")


def validate_feature_configuration(
    configuration: dict[str, Any],
) -> None:
    if not configuration:
        raise ValueError("Feature configuration cannot be empty.")

    features = configuration.get("features")

    if not isinstance(features, list) or not features:
        raise ValueError("Feature configuration must include a non-empty 'features' list.")
