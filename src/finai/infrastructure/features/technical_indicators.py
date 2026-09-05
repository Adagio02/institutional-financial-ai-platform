import pandas as pd

from finai.domain.features.validation import (
    validate_positive_window,
)


def calculate_relative_strength_index(
    close_prices: pd.Series,
    *,
    window: int = 14,
) -> pd.Series:
    validate_positive_window(window)

    price_change = close_prices.astype(float).diff()
    gains = price_change.clip(lower=0.0)
    losses = -price_change.clip(upper=0.0)

    average_gain = gains.rolling(
        window=window,
        min_periods=window,
    ).mean()

    average_loss = losses.rolling(
        window=window,
        min_periods=window,
    ).mean()

    relative_strength = average_gain / average_loss.replace(
        0.0,
        float("nan"),
    )

    return 100.0 - (100.0 / (1.0 + relative_strength))


def calculate_macd(
    close_prices: pd.Series,
    *,
    fast_window: int = 12,
    slow_window: int = 26,
    signal_window: int = 9,
) -> pd.DataFrame:
    validate_positive_window(fast_window)
    validate_positive_window(slow_window)
    validate_positive_window(signal_window)

    if fast_window >= slow_window:
        raise ValueError("fast_window must be smaller than slow_window.")

    prices = close_prices.astype(float)

    fast_average = prices.ewm(
        span=fast_window,
        adjust=False,
    ).mean()

    slow_average = prices.ewm(
        span=slow_window,
        adjust=False,
    ).mean()

    macd_line = fast_average - slow_average

    signal_line = macd_line.ewm(
        span=signal_window,
        adjust=False,
    ).mean()

    return pd.DataFrame(
        {
            "macd": macd_line,
            "macd_signal": signal_line,
            "macd_histogram": (macd_line - signal_line),
        },
        index=close_prices.index,
    )


def calculate_average_true_range(
    high_prices: pd.Series,
    low_prices: pd.Series,
    close_prices: pd.Series,
    *,
    window: int = 14,
) -> pd.Series:
    validate_positive_window(window)

    high = high_prices.astype(float)
    low = low_prices.astype(float)
    previous_close = close_prices.astype(float).shift(1)

    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return true_range.rolling(
        window=window,
        min_periods=window,
    ).mean()
