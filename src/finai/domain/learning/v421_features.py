from __future__ import annotations

import numpy as np
import pandas as pd

from finai.domain.learning.v41_features import (
    V41_FEATURE_COLUMNS,
    build_v41_features,
)


V421_FEATURE_COLUMNS = list(V41_FEATURE_COLUMNS)


MARKET_TIMEZONE = "America/New_York"

MARKET_OPEN_MINUTE = 9 * 60 + 30

MARKET_CLOSE_MINUTE = 16 * 60


def apply_v421_session_features(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    """
    Replace the V4.1 fixed-UTC session features
    with DST-aware New York market-clock features.

    The input timestamps remain UTC in the returned
    frame. Only feature calculation is performed in
    America/New_York local time.

    This makes:

        09:30 New York == market open

    regardless of whether the date falls in EST or EDT.
    """

    if "timestamp" not in frame.columns:
        raise ValueError("V4.2.1 session features require a timestamp column.")

    result = frame.copy()

    timestamp_utc = pd.to_datetime(
        result["timestamp"],
        utc=True,
    )

    timestamp_new_york = timestamp_utc.dt.tz_convert(MARKET_TIMEZONE)

    minute_of_day = timestamp_new_york.dt.hour * 60 + timestamp_new_york.dt.minute

    angle = 2.0 * np.pi * minute_of_day / 1440.0

    result["minute_sin"] = np.sin(angle)

    result["minute_cos"] = np.cos(angle)

    result["minutes_from_open"] = minute_of_day - MARKET_OPEN_MINUTE

    result["minutes_to_close"] = MARKET_CLOSE_MINUTE - minute_of_day

    result["opening_session"] = (
        (result["minutes_from_open"] >= 0) & (result["minutes_from_open"] < 60)
    ).astype(float)

    result["closing_session"] = (
        (result["minutes_to_close"] >= 0) & (result["minutes_to_close"] < 60)
    ).astype(float)

    return result


def build_v421_features(
    *,
    target_bars: pd.DataFrame,
    spy_bars: pd.DataFrame,
    qqq_bars: pd.DataFrame,
    forward_horizon_bars: int,
    minimum_edge_bps: float,
    round_trip_cost_bps: float = 0.0,
    include_target: bool = True,
) -> pd.DataFrame:
    """
    Build the V4.1 multi-market feature set and then
    replace only the time/session features with the
    V4.2.1 DST-aware implementation.

    All predictive feature names remain compatible
    with V4.1 model templates.
    """

    dataset = build_v41_features(
        target_bars=target_bars,
        spy_bars=spy_bars,
        qqq_bars=qqq_bars,
        forward_horizon_bars=(forward_horizon_bars),
        minimum_edge_bps=(minimum_edge_bps),
        round_trip_cost_bps=(round_trip_cost_bps),
        include_target=(include_target),
    )

    dataset = apply_v421_session_features(dataset)

    required = list(V421_FEATURE_COLUMNS)

    if include_target:
        required.extend(
            [
                "forward_return",
                "target",
            ]
        )

    dataset = dataset.replace(
        [
            np.inf,
            -np.inf,
        ],
        np.nan,
    )

    dataset = dataset.dropna(subset=required)

    if include_target:
        dataset["target"] = dataset["target"].astype(int)

    return dataset.reset_index(drop=True)
