from __future__ import annotations

import numpy as np
import pandas as pd


FEATURE_COLUMNS = [
    "return_1",
    "return_2",
    "return_5",
    "return_10",
    "return_20",
    "range_fraction",
    "body_fraction",
    "volume_change",
    "volume_zscore_20",
    "volatility_5",
    "volatility_10",
    "volatility_20",
    "price_vs_ma_5",
    "price_vs_ma_10",
    "price_vs_ma_20",
    "ma_5_vs_20",
    "momentum_5_20",
    "rsi_14",
    "hour_sin",
    "hour_cos",
]


def _rsi(
    close: pd.Series,
    window: int = 14,
) -> pd.Series:
    delta = close.diff()

    gain = delta.clip(
        lower=0.0
    )

    loss = (
        -delta.clip(
            upper=0.0
        )
    )

    average_gain = gain.rolling(
        window
    ).mean()

    average_loss = loss.rolling(
        window
    ).mean()

    relative_strength = (
        average_gain
        / average_loss.replace(
            0.0,
            np.nan,
        )
    )

    return (
        100.0
        - (
            100.0
            / (
                1.0
                + relative_strength
            )
        )
    )


def build_features(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    result = frame.copy()

    close = result["close"].astype(
        float
    )

    open_price = result["open"].astype(
        float
    )

    high = result["high"].astype(
        float
    )

    low = result["low"].astype(
        float
    )

    volume = result["volume"].astype(
        float
    )

    result["return_1"] = (
        close.pct_change(1)
    )

    result["return_2"] = (
        close.pct_change(2)
    )

    result["return_5"] = (
        close.pct_change(5)
    )

    result["return_10"] = (
        close.pct_change(10)
    )

    result["return_20"] = (
        close.pct_change(20)
    )

    result["range_fraction"] = (
        (high - low)
        / close
    )

    result["body_fraction"] = (
        (close - open_price)
        / open_price
    )

    result["volume_change"] = (
        volume.pct_change()
    )

    volume_mean = volume.rolling(
        20
    ).mean()

    volume_std = volume.rolling(
        20
    ).std()

    result["volume_zscore_20"] = (
        (volume - volume_mean)
        / volume_std.replace(
            0.0,
            np.nan,
        )
    )

    returns = close.pct_change()

    result["volatility_5"] = (
        returns.rolling(
            5
        ).std()
    )

    result["volatility_10"] = (
        returns.rolling(
            10
        ).std()
    )

    result["volatility_20"] = (
        returns.rolling(
            20
        ).std()
    )

    ma_5 = close.rolling(
        5
    ).mean()

    ma_10 = close.rolling(
        10
    ).mean()

    ma_20 = close.rolling(
        20
    ).mean()

    result["price_vs_ma_5"] = (
        close / ma_5 - 1.0
    )

    result["price_vs_ma_10"] = (
        close / ma_10 - 1.0
    )

    result["price_vs_ma_20"] = (
        close / ma_20 - 1.0
    )

    result["ma_5_vs_20"] = (
        ma_5 / ma_20 - 1.0
    )

    result["momentum_5_20"] = (
        result["return_5"]
        - result["return_20"]
    )

    result["rsi_14"] = (
        _rsi(close)
        / 100.0
    )

    timestamp = pd.to_datetime(
        result["timestamp"],
        utc=True,
    )

    minute_of_day = (
        timestamp.dt.hour * 60
        + timestamp.dt.minute
    )

    angle = (
        2.0
        * np.pi
        * minute_of_day
        / 1440.0
    )

    result["hour_sin"] = np.sin(
        angle
    )

    result["hour_cos"] = np.cos(
        angle
    )

    result = result.replace(
        [
            np.inf,
            -np.inf,
        ],
        np.nan,
    )

    return result