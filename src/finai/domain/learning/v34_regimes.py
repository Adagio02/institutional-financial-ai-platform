from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(
    frozen=True,
    slots=True,
)
class V34RegimeBoundaries:
    low_volatility: float
    high_volatility: float
    trend_threshold: float


def calculate_regime_boundaries(
    research: pd.DataFrame,
) -> V34RegimeBoundaries:
    volatility = (
        research[
            "volatility_20"
        ]
        .astype(float)
    )

    trend = (
        research[
            "price_vs_ma_20"
        ]
        .astype(float)
        .abs()
    )

    return V34RegimeBoundaries(
        low_volatility=float(
            volatility.quantile(
                0.33
            )
        ),
        high_volatility=float(
            volatility.quantile(
                0.67
            )
        ),
        trend_threshold=float(
            trend.quantile(
                0.50
            )
        ),
    )


def assign_regimes(
    frame: pd.DataFrame,
    *,
    boundaries: V34RegimeBoundaries,
) -> pd.Series:
    volatility = (
        frame[
            "volatility_20"
        ]
        .astype(float)
    )

    trend = (
        frame[
            "price_vs_ma_20"
        ]
        .astype(float)
        .abs()
    )

    regimes = []

    for (
        volatility_value,
        trend_value,
    ) in zip(
        volatility,
        trend,
        strict=True,
    ):
        if (
            volatility_value
            <= boundaries.low_volatility
        ):
            volatility_regime = (
                "low_vol"
            )

        elif (
            volatility_value
            >= boundaries.high_volatility
        ):
            volatility_regime = (
                "high_vol"
            )

        else:
            volatility_regime = (
                "mid_vol"
            )

        if (
            trend_value
            >= boundaries.trend_threshold
        ):
            trend_regime = "trend"

        else:
            trend_regime = "range"

        regimes.append(
            (
                volatility_regime
                + "_"
                + trend_regime
            )
        )

    return pd.Series(
        regimes,
        index=frame.index,
        dtype="object",
    )