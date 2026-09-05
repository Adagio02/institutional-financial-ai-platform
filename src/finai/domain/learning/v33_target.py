from __future__ import annotations

import numpy as np
import pandas as pd


def build_target(
    frame: pd.DataFrame,
    *,
    forward_horizon_bars: int,
    volatility_multiplier: float,
    round_trip_cost_bps: float,
) -> pd.DataFrame:
    if forward_horizon_bars <= 0:
        raise ValueError(
            "forward_horizon_bars must "
            "be positive."
        )

    if volatility_multiplier < 0.0:
        raise ValueError(
            "volatility_multiplier cannot "
            "be negative."
        )

    result = frame.copy()

    close = result["close"].astype(
        float
    )

    future_close = close.shift(
        -forward_horizon_bars
    )

    result["forward_return"] = (
        future_close / close - 1.0
    )

    volatility = (
        close
        .pct_change()
        .rolling(20)
        .std()
    )

    cost_fraction = (
        round_trip_cost_bps
        / 10_000.0
    )

    dynamic_edge = np.maximum(
        volatility
        * volatility_multiplier,
        cost_fraction,
    )

    result["target_edge"] = (
        dynamic_edge
    )

    result["target"] = 0

    result.loc[
        result["forward_return"]
        > dynamic_edge,
        "target",
    ] = 1

    result.loc[
        result["forward_return"]
        < -dynamic_edge,
        "target",
    ] = -1

    return result