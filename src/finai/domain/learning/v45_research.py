from __future__ import annotations

import math
from statistics import mean, pstdev
from typing import Any

import numpy as np


DIRECTION_BOTH = "both"
DIRECTION_LONG = "long_only"
DIRECTION_SHORT = "short_only"

DIRECTIONS = (
    DIRECTION_BOTH,
    DIRECTION_LONG,
    DIRECTION_SHORT,
)

THRESHOLD_GRID = (
    0.50,
    0.525,
    0.55,
    0.575,
    0.60,
    0.625,
    0.65,
    0.675,
    0.70,
)

FEATURE_VARIANTS = (
    "baseline",
    "baseline_plus_price_structure",
    "baseline_plus_volume_structure",
    "baseline_plus_market_relative",
    "baseline_plus_session_state",
    "baseline_plus_regime_state",
    "all_engineered",
)


def probability_columns(
    probabilities: np.ndarray,
    classes: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mapping = {
        int(value): index
        for index, value in enumerate(classes)
    }
    row_count = len(probabilities)
    zeros = np.zeros(row_count, dtype=float)

    short_probability = (
        probabilities[:, mapping[-1]]
        if -1 in mapping
        else zeros
    )
    hold_probability = (
        probabilities[:, mapping[0]]
        if 0 in mapping
        else zeros
    )
    long_probability = (
        probabilities[:, mapping[1]]
        if 1 in mapping
        else zeros
    )
    return (
        short_probability,
        hold_probability,
        long_probability,
    )


def directional_positions(
    *,
    probabilities: np.ndarray,
    classes: np.ndarray,
    threshold: float,
    direction: str,
) -> np.ndarray:
    short_probability, hold_probability, long_probability = (
        probability_columns(
            probabilities=probabilities,
            classes=classes,
        )
    )

    positions = np.zeros(
        len(probabilities),
        dtype=int,
    )

    if direction in (
        DIRECTION_BOTH,
        DIRECTION_LONG,
    ):
        long_mask = (
            (long_probability >= float(threshold))
            & (long_probability > short_probability)
            & (long_probability > hold_probability)
        )
        positions[long_mask] = 1

    if direction in (
        DIRECTION_BOTH,
        DIRECTION_SHORT,
    ):
        short_mask = (
            (short_probability >= float(threshold))
            & (short_probability > long_probability)
            & (short_probability > hold_probability)
        )
        positions[short_mask] = -1

    return positions


def selection_penalty(
    fold_returns: list[float],
    *,
    trial_count: int,
) -> dict[str, float]:
    if not fold_returns:
        return {
            "mean_fold_return": 0.0,
            "fold_std": 0.0,
            "selection_penalty": 0.0,
            "penalized_mean_fold_return": 0.0,
        }

    mu = float(mean(fold_returns))
    sigma = (
        float(pstdev(fold_returns))
        if len(fold_returns) > 1
        else 0.0
    )
    trials = max(2, int(trial_count))
    penalty = (
        sigma
        * math.sqrt(2.0 * math.log(trials))
        / math.sqrt(max(1, len(fold_returns)))
    )
    return {
        "mean_fold_return": mu,
        "fold_std": sigma,
        "selection_penalty": float(penalty),
        "penalized_mean_fold_return": float(
            mu - penalty
        ),
    }


def research_eligible(
    item: dict[str, Any],
    *,
    minimum_positive_fold_fraction: float,
    minimum_trades: int,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    if float(item.get("net_return", 0.0)) <= 0.0:
        reasons.append("non_positive_net_return")

    if (
        float(
            item.get(
                "positive_fold_fraction",
                0.0,
            )
        )
        < float(minimum_positive_fold_fraction)
    ):
        reasons.append(
            "insufficient_positive_fold_fraction"
        )

    if int(item.get("trade_count", 0)) < int(
        minimum_trades
    ):
        reasons.append("insufficient_trade_count")

    if (
        float(
            item.get(
                "penalized_mean_fold_return",
                0.0,
            )
        )
        <= 0.0
    ):
        reasons.append(
            "non_positive_selection_adjusted_expectancy"
        )

    return len(reasons) == 0, reasons
