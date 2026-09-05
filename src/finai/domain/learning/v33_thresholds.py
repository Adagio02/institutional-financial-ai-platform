from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(
    frozen=True,
    slots=True,
)
class ThresholdResult:
    long_threshold: float
    short_threshold: float

    net_return: float
    trade_count: int
    turnover: float
    maximum_drawdown: float

    score: float


def probabilities_to_positions(
    *,
    probabilities: np.ndarray,
    classes: np.ndarray,
    long_threshold: float,
    short_threshold: float,
) -> np.ndarray:
    class_to_index = {
        int(value): index
        for index, value
        in enumerate(classes)
    }

    positions = np.zeros(
        probabilities.shape[0],
        dtype=float,
    )

    long_index = class_to_index.get(
        1
    )

    short_index = class_to_index.get(
        -1
    )

    if long_index is not None:
        long_mask = (
            probabilities[
                :,
                long_index,
            ]
            >= long_threshold
        )

        positions[
            long_mask
        ] = 1.0

    if short_index is not None:
        short_probability = (
            probabilities[
                :,
                short_index,
            ]
        )

        short_mask = (
            short_probability
            >= short_threshold
        )

        if long_index is not None:
            long_probability = (
                probabilities[
                    :,
                    long_index,
                ]
            )

            short_mask &= (
                short_probability
                > long_probability
            )

        positions[
            short_mask
        ] = -1.0

    return positions


def evaluate_positions(
    *,
    positions: np.ndarray,
    forward_returns: np.ndarray,
    round_trip_cost_bps: float,
) -> tuple[
    float,
    int,
    float,
    float,
]:
    previous = np.concatenate(
        (
            np.array([0.0]),
            positions[:-1],
        )
    )

    changes = np.abs(
        positions
        - previous
    )

    cost_rate = (
        round_trip_cost_bps
        / 10_000.0
        / 2.0
    )

    strategy_returns = (
        positions
        * forward_returns
        - changes
        * cost_rate
    )

    equity = np.cumprod(
        1.0
        + strategy_returns
    )

    if len(equity) == 0:
        maximum_drawdown = 0.0
    else:
        running_maximum = (
            np.maximum.accumulate(
                equity
            )
        )

        drawdown = (
            equity
            / running_maximum
            - 1.0
        )

        maximum_drawdown = float(
            abs(
                np.min(
                    drawdown
                )
            )
        )

    net_return = float(
        np.prod(
            1.0
            + strategy_returns
        )
        - 1.0
    )

    trade_count = int(
        np.count_nonzero(
            changes > 0.0
        )
    )

    turnover = float(
        changes.sum()
    )

    return (
        net_return,
        trade_count,
        turnover,
        maximum_drawdown,
    )


def optimize_thresholds(
    *,
    probabilities: np.ndarray,
    classes: np.ndarray,
    forward_returns: np.ndarray,
    long_thresholds: list[float],
    short_thresholds: list[float],
    round_trip_cost_bps: float,
    minimum_trades: int,
) -> ThresholdResult:
    best: ThresholdResult | None = None

    for long_threshold in long_thresholds:
        for short_threshold in short_thresholds:
            positions = (
                probabilities_to_positions(
                    probabilities=probabilities,
                    classes=classes,
                    long_threshold=(
                        long_threshold
                    ),
                    short_threshold=(
                        short_threshold
                    ),
                )
            )

            (
                net_return,
                trade_count,
                turnover,
                maximum_drawdown,
            ) = evaluate_positions(
                positions=positions,
                forward_returns=(
                    forward_returns
                ),
                round_trip_cost_bps=(
                    round_trip_cost_bps
                ),
            )

            if trade_count < minimum_trades:
                continue

            score = (
                net_return
                - 0.50
                * maximum_drawdown
                - 0.00001
                * turnover
            )

            result = ThresholdResult(
                long_threshold=(
                    long_threshold
                ),
                short_threshold=(
                    short_threshold
                ),
                net_return=net_return,
                trade_count=trade_count,
                turnover=turnover,
                maximum_drawdown=(
                    maximum_drawdown
                ),
                score=score,
            )

            if (
                best is None
                or result.score
                > best.score
            ):
                best = result

    if best is None:
        raise RuntimeError(
            "No threshold configuration "
            "satisfied minimum_trades."
        )

    return best