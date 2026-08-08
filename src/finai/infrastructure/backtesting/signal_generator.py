from finai.domain.backtesting.enums import (
    SignalDirection,
)


def generate_classification_signal(
    *,
    probability: float,
    long_threshold: float,
    short_threshold: float,
    allow_short: bool,
) -> SignalDirection:
    if probability >= long_threshold:
        return SignalDirection.LONG

    if allow_short and probability <= short_threshold:
        return SignalDirection.SHORT

    return SignalDirection.FLAT


def generate_regression_signal(
    *,
    prediction: float,
    long_threshold: float,
    short_threshold: float,
    allow_short: bool,
) -> SignalDirection:
    if prediction >= long_threshold:
        return SignalDirection.LONG

    if allow_short and prediction <= short_threshold:
        return SignalDirection.SHORT

    return SignalDirection.FLAT
