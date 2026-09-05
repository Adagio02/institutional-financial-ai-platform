import numpy as np
import pandas as pd

from finai.domain.features.validation import (
    validate_positive_window,
)


def calculate_simple_return(
    close_prices: pd.Series,
    *,
    periods: int = 1,
) -> pd.Series:
    validate_positive_window(periods)

    return close_prices.astype(float).pct_change(
        periods=periods,
        fill_method=None,
    )


def calculate_log_return(
    close_prices: pd.Series,
    *,
    periods: int = 1,
) -> pd.Series:
    validate_positive_window(periods)

    prices = close_prices.astype(float)

    return np.log(prices / prices.shift(periods))


def calculate_momentum(
    close_prices: pd.Series,
    *,
    window: int = 10,
) -> pd.Series:
    validate_positive_window(window)

    return close_prices.astype(float).diff(periods=window)


def calculate_volume_change(
    volumes: pd.Series,
    *,
    periods: int = 1,
) -> pd.Series:
    validate_positive_window(periods)

    return volumes.astype(float).pct_change(
        periods=periods,
        fill_method=None,
    )
