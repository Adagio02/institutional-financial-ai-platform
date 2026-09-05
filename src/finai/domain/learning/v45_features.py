from __future__ import annotations

import numpy as np
import pandas as pd

from finai.domain.learning.v421_features import (
    V421_FEATURE_COLUMNS,
)


V45_ENGINEERED_FEATURE_COLUMNS = [
    # Multi-scale price structure
    "return_acceleration_5_15",
    "return_acceleration_15_60",
    "volatility_ratio_5_20",
    "volatility_ratio_20_60",
    "range_location_20",
    "range_location_60",
    "distance_from_high_20",
    "distance_from_low_20",

    # Volume/liquidity structure
    "relative_volume_5_60",
    "relative_volume_20_60",
    "volume_trend_5_20",
    "return_volume_interaction_5",
    "range_volume_interaction",

    # Cross-market structure
    "spy_qqq_agreement_5",
    "spy_qqq_agreement_15",
    "market_return_5",
    "market_return_15",
    "market_return_60",
    "relative_strength_5",
    "relative_strength_15",
    "relative_strength_60",
    "relative_strength_acceleration",
    "market_volatility_spread",

    # Session state
    "return_since_open",
    "distance_from_session_high",
    "distance_from_session_low",
    "session_range_pct",
    "relative_session_volume",

    # Observable regime state
    "trend_signed",
    "volatility_regime_ratio",
    "market_trend_alignment",
    "relative_strength_regime",
]

V45_FEATURE_COLUMNS = list(V421_FEATURE_COLUMNS) + list(
    V45_ENGINEERED_FEATURE_COLUMNS
)

V45_FEATURE_FAMILIES: dict[str, tuple[str, ...]] = {
    "baseline": tuple(V421_FEATURE_COLUMNS),
    "price_structure": (
        "return_acceleration_5_15",
        "return_acceleration_15_60",
        "volatility_ratio_5_20",
        "volatility_ratio_20_60",
        "range_location_20",
        "range_location_60",
        "distance_from_high_20",
        "distance_from_low_20",
    ),
    "volume_structure": (
        "relative_volume_5_60",
        "relative_volume_20_60",
        "volume_trend_5_20",
        "return_volume_interaction_5",
        "range_volume_interaction",
    ),
    "market_relative": (
        "spy_qqq_agreement_5",
        "spy_qqq_agreement_15",
        "market_return_5",
        "market_return_15",
        "market_return_60",
        "relative_strength_5",
        "relative_strength_15",
        "relative_strength_60",
        "relative_strength_acceleration",
        "market_volatility_spread",
    ),
    "session_state": (
        "return_since_open",
        "distance_from_session_high",
        "distance_from_session_low",
        "session_range_pct",
        "relative_session_volume",
    ),
    "regime_state": (
        "trend_signed",
        "volatility_regime_ratio",
        "market_trend_alignment",
        "relative_strength_regime",
    ),
}


def _safe_divide(
    numerator: pd.Series,
    denominator: pd.Series,
) -> pd.Series:
    return numerator / denominator.replace(0.0, np.nan)


def _session_group_key(
    timestamp: pd.Series,
) -> pd.Series:
    local = pd.to_datetime(
        timestamp,
        utc=True,
    ).dt.tz_convert(
        "America/New_York"
    )
    return local.dt.date


def apply_v45_features(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add causal V4.5 features to the existing V4.2.1 dataset.

    Every engineered value uses current/past rows only. No forward_return
    or target value is used to construct a predictive feature.
    """
    result = frame.copy()

    required_raw = {
        "timestamp",
        "high_price",
        "low_price",
        "close_price",
        "volume",
        "spy_close",
        "qqq_close",
    }
    missing = sorted(
        required_raw - set(result.columns)
    )
    if missing:
        raise ValueError(
            "V4.5 dataset is missing raw columns: "
            + ", ".join(missing)
        )

    close = result["close_price"].astype(float)
    high = result["high_price"].astype(float)
    low = result["low_price"].astype(float)
    volume = result["volume"].astype(float)

    result["return_acceleration_5_15"] = (
        result["return_5"]
        - result["return_15"] / 3.0
    )
    result["return_acceleration_15_60"] = (
        result["return_15"]
        - result["return_60"] / 4.0
    )
    result["volatility_ratio_5_20"] = _safe_divide(
        result["volatility_5"],
        result["volatility_20"],
    )
    result["volatility_ratio_20_60"] = _safe_divide(
        result["volatility_20"],
        result["volatility_60"],
    )

    high_20 = high.rolling(20).max()
    low_20 = low.rolling(20).min()
    high_60 = high.rolling(60).max()
    low_60 = low.rolling(60).min()

    result["range_location_20"] = _safe_divide(
        close - low_20,
        high_20 - low_20,
    )
    result["range_location_60"] = _safe_divide(
        close - low_60,
        high_60 - low_60,
    )
    result["distance_from_high_20"] = _safe_divide(
        close - high_20,
        high_20,
    )
    result["distance_from_low_20"] = _safe_divide(
        close - low_20,
        low_20,
    )

    volume_5 = volume.rolling(5).mean()
    volume_20 = volume.rolling(20).mean()
    volume_60 = volume.rolling(60).mean()

    result["relative_volume_5_60"] = _safe_divide(
        volume_5,
        volume_60,
    )
    result["relative_volume_20_60"] = _safe_divide(
        volume_20,
        volume_60,
    )
    result["volume_trend_5_20"] = _safe_divide(
        volume_5 - volume_20,
        volume_20,
    )
    result["return_volume_interaction_5"] = (
        result["return_5"]
        * result["relative_volume_5_60"]
    )
    result["range_volume_interaction"] = (
        result["range_pct"]
        * result["relative_volume_20_60"]
    )

    spy_return_5 = result["spy_return_5"]
    qqq_return_5 = result["qqq_return_5"]
    spy_return_15 = result["spy_return_15"]
    qqq_return_15 = result["qqq_return_15"]

    result["spy_qqq_agreement_5"] = (
        np.sign(spy_return_5)
        == np.sign(qqq_return_5)
    ).astype(float)
    result["spy_qqq_agreement_15"] = (
        np.sign(spy_return_15)
        == np.sign(qqq_return_15)
    ).astype(float)

    for horizon in (5, 15, 60):
        market_return = (
            result[f"spy_return_{horizon}"]
            + result[f"qqq_return_{horizon}"]
        ) / 2.0
        result[f"market_return_{horizon}"] = market_return
        result[f"relative_strength_{horizon}"] = (
            result[f"return_{horizon}"]
            - market_return
        )

    result["relative_strength_acceleration"] = (
        result["relative_strength_5"]
        - result["relative_strength_60"] / 12.0
    )
    result["market_volatility_spread"] = (
        result["spy_volatility_20"]
        - result["qqq_volatility_20"]
    ).abs()

    session_key = _session_group_key(
        result["timestamp"]
    )
    grouped_close = close.groupby(session_key)
    grouped_high = high.groupby(session_key)
    grouped_low = low.groupby(session_key)
    grouped_volume = volume.groupby(session_key)

    session_open = grouped_close.transform("first")
    session_high = grouped_high.cummax()
    session_low = grouped_low.cummin()
    session_cum_volume = grouped_volume.cumsum()
    session_bar_number = (
        result.groupby(session_key)
        .cumcount()
        .astype(float)
        + 1.0
    )
    session_average_volume = (
        session_cum_volume
        / session_bar_number
    )

    result["return_since_open"] = _safe_divide(
        close - session_open,
        session_open,
    )
    result["distance_from_session_high"] = _safe_divide(
        close - session_high,
        session_high,
    )
    result["distance_from_session_low"] = _safe_divide(
        close - session_low,
        session_low,
    )
    result["session_range_pct"] = _safe_divide(
        session_high - session_low,
        close,
    )
    result["relative_session_volume"] = _safe_divide(
        volume,
        session_average_volume,
    )

    trend_sign = np.sign(
        result["ema_gap_10_30"]
    )
    market_sign = np.sign(
        result["market_return_15"]
    )
    relative_sign = np.sign(
        result["relative_strength_15"]
    )

    result["trend_signed"] = (
        result["trend_strength"]
        * trend_sign
    )
    result["volatility_regime_ratio"] = _safe_divide(
        result["volatility_20"],
        result["volatility_60"],
    )
    result["market_trend_alignment"] = (
        trend_sign == market_sign
    ).astype(float)
    result["relative_strength_regime"] = (
        relative_sign
        * result["relative_strength_15"].abs()
        * result["relative_volume_20_60"]
    )

    result = result.replace(
        [np.inf, -np.inf],
        np.nan,
    )
    result = result.dropna(
        subset=V45_FEATURE_COLUMNS
    )

    return result.reset_index(drop=True)
