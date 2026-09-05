import numpy as np
import pandas as pd

from finai.domain.features.validation import (
    validate_positive_window,
)


def calculate_rolling_mean(
    values: pd.Series,
    *,
    window: int,
) -> pd.Series:
    validate_positive_window(window)

    return (
        values.astype(float)
        .rolling(
            window=window,
            min_periods=window,
        )
        .mean()
    )


def calculate_rolling_standard_deviation(
    values: pd.Series,
    *,
    window: int,
) -> pd.Series:
    validate_positive_window(window)

    return (
        values.astype(float)
        .rolling(
            window=window,
            min_periods=window,
        )
        .std()
    )


def calculate_rolling_volatility(
    returns: pd.Series,
    *,
    window: int,
    annualization_factor: int = 252,
) -> pd.Series:
    validate_positive_window(window)
    validate_positive_window(annualization_factor)

    rolling_standard_deviation = (
        returns.astype(float)
        .rolling(
            window=window,
            min_periods=window,
        )
        .std()
    )

    return rolling_standard_deviation * np.sqrt(annualization_factor)


def calculate_drawdown(
    close_prices: pd.Series,
) -> pd.Series:
    prices = close_prices.astype(float)
    running_maximum = prices.cummax()

    return (prices / running_maximum) - 1.0
