from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import (
    confusion_matrix,
    precision_recall_fscore_support,
)


SELL = -1
HOLD = 0
BUY = 1


V43_CONFIDENCE_BUCKETS = (
    (0.35, 0.40),
    (0.40, 0.45),
    (0.45, 0.50),
    (0.50, 0.55),
    (0.55, 0.60),
    (0.60, 0.65),
    (0.65, 0.70),
    (0.70, 1.01),
)


def probability_map(
    *,
    probabilities: np.ndarray,
    classes: np.ndarray,
) -> dict[int, np.ndarray]:
    normalized_probabilities = np.asarray(
        probabilities,
        dtype=float,
    )

    normalized_classes = np.asarray(
        classes,
        dtype=int,
    )

    return {
        int(label): normalized_probabilities[
            :,
            index,
        ]
        for index, label in enumerate(normalized_classes)
    }


def probability_columns(
    *,
    probabilities: np.ndarray,
    classes: np.ndarray,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    mapped = probability_map(
        probabilities=probabilities,
        classes=classes,
    )

    row_count = len(probabilities)

    short_probability = mapped.get(
        SELL,
        np.zeros(
            row_count,
            dtype=float,
        ),
    )

    hold_probability = mapped.get(
        HOLD,
        np.zeros(
            row_count,
            dtype=float,
        ),
    )

    long_probability = mapped.get(
        BUY,
        np.zeros(
            row_count,
            dtype=float,
        ),
    )

    return (
        np.asarray(
            short_probability,
            dtype=float,
        ),
        np.asarray(
            hold_probability,
            dtype=float,
        ),
        np.asarray(
            long_probability,
            dtype=float,
        ),
    )


def select_non_overlapping_indices(
    *,
    eligible: np.ndarray,
    horizon: int,
) -> np.ndarray:
    normalized = np.asarray(
        eligible,
        dtype=bool,
    )

    normalized_horizon = max(
        1,
        int(horizon),
    )

    selected: list[int] = []

    index = 0

    while index < len(normalized):
        if not normalized[index]:
            index += 1
            continue

        selected.append(index)

        index += normalized_horizon

    return np.asarray(
        selected,
        dtype=int,
    )


def event_trade_returns(
    *,
    positions: np.ndarray,
    forward_returns: np.ndarray,
    horizon: int,
    round_trip_cost_bps: float,
) -> np.ndarray:
    normalized_positions = np.asarray(
        positions,
        dtype=int,
    )

    normalized_returns = np.asarray(
        forward_returns,
        dtype=float,
    )

    if len(normalized_positions) != len(normalized_returns):
        raise ValueError("positions and forward_returns must have equal length.")

    eligible = (normalized_positions != 0) & np.isfinite(normalized_returns)

    selected = select_non_overlapping_indices(
        eligible=eligible,
        horizon=horizon,
    )

    if len(selected) == 0:
        return np.asarray(
            [],
            dtype=float,
        )

    gross = normalized_positions[selected].astype(float) * normalized_returns[selected]

    round_trip_cost = float(round_trip_cost_bps) / 10_000.0

    return gross - round_trip_cost


def event_trade_metrics(
    *,
    positions: np.ndarray,
    forward_returns: np.ndarray,
    horizon: int,
    round_trip_cost_bps: float,
) -> dict[str, Any]:
    trades = event_trade_returns(
        positions=positions,
        forward_returns=(forward_returns),
        horizon=horizon,
        round_trip_cost_bps=(round_trip_cost_bps),
    )

    if len(trades) == 0:
        return {
            "trade_count": 0,
            "win_rate": 0.0,
            "mean_net_return": 0.0,
            "median_net_return": 0.0,
            "mean_net_bps": 0.0,
            "median_net_bps": 0.0,
            "compounded_net_return": 0.0,
        }

    compounded = float(np.prod(1.0 + trades) - 1.0)

    return {
        "trade_count": int(len(trades)),
        "win_rate": float(np.mean(trades > 0.0)),
        "mean_net_return": float(np.mean(trades)),
        "median_net_return": float(np.median(trades)),
        "mean_net_bps": float(np.mean(trades) * 10_000.0),
        "median_net_bps": float(np.median(trades) * 10_000.0),
        "compounded_net_return": (compounded),
    }


def classification_diagnostics(
    *,
    actual: np.ndarray,
    predicted: np.ndarray,
) -> dict[str, Any]:
    normalized_actual = np.asarray(
        actual,
        dtype=int,
    )

    normalized_predicted = np.asarray(
        predicted,
        dtype=int,
    )

    labels = [
        SELL,
        HOLD,
        BUY,
    ]

    matrix = confusion_matrix(
        normalized_actual,
        normalized_predicted,
        labels=labels,
    )

    (
        precision,
        recall,
        f1,
        support,
    ) = precision_recall_fscore_support(
        normalized_actual,
        normalized_predicted,
        labels=labels,
        zero_division=0,
    )

    names = [
        "short",
        "hold",
        "long",
    ]

    per_class: dict[
        str,
        dict[str, Any],
    ] = {}

    for index, name in enumerate(names):
        per_class[name] = {
            "label": int(labels[index]),
            "precision": float(precision[index]),
            "recall": float(recall[index]),
            "f1": float(f1[index]),
            "support": int(support[index]),
            "predicted_count": int(np.sum(normalized_predicted == labels[index])),
        }

    return {
        "labels": labels,
        "label_names": names,
        "confusion_matrix": (matrix.astype(int).tolist()),
        "per_class": per_class,
        "actual_counts": {
            name: int(np.sum(normalized_actual == label))
            for name, label in zip(
                names,
                labels,
                strict=True,
            )
        },
        "predicted_counts": {
            name: int(np.sum(normalized_predicted == label))
            for name, label in zip(
                names,
                labels,
                strict=True,
            )
        },
    }


def multiclass_brier_score(
    *,
    actual: np.ndarray,
    short_probability: np.ndarray,
    hold_probability: np.ndarray,
    long_probability: np.ndarray,
) -> float:
    normalized_actual = np.asarray(
        actual,
        dtype=int,
    )

    probability_matrix = np.column_stack(
        [
            short_probability,
            hold_probability,
            long_probability,
        ]
    ).astype(float)

    target_matrix = np.column_stack(
        [
            (normalized_actual == SELL).astype(float),
            (normalized_actual == HOLD).astype(float),
            (normalized_actual == BUY).astype(float),
        ]
    )

    return float(
        np.mean(
            np.sum(
                (probability_matrix - target_matrix) ** 2,
                axis=1,
            )
        )
    )


def confidence_bucket_diagnostics(
    *,
    short_probability: np.ndarray,
    hold_probability: np.ndarray,
    long_probability: np.ndarray,
    forward_returns: np.ndarray,
    horizon: int,
    round_trip_cost_bps: float,
) -> list[dict[str, Any]]:
    short_probability = np.asarray(
        short_probability,
        dtype=float,
    )

    hold_probability = np.asarray(
        hold_probability,
        dtype=float,
    )

    long_probability = np.asarray(
        long_probability,
        dtype=float,
    )

    forward_returns = np.asarray(
        forward_returns,
        dtype=float,
    )

    results: list[dict[str, Any]] = []

    for direction in (
        "long",
        "short",
    ):
        if direction == "long":
            signal_probability = long_probability

            dominant = (long_probability > short_probability) & (
                long_probability > hold_probability
            )

            position_value = BUY

        else:
            signal_probability = short_probability

            dominant = (short_probability > long_probability) & (
                short_probability > hold_probability
            )

            position_value = SELL

        for (
            lower,
            upper,
        ) in V43_CONFIDENCE_BUCKETS:
            bucket_mask = dominant & (signal_probability >= lower) & (signal_probability < upper)

            positions = np.zeros(
                len(forward_returns),
                dtype=int,
            )

            positions[bucket_mask] = position_value

            metrics = event_trade_metrics(
                positions=positions,
                forward_returns=(forward_returns),
                horizon=horizon,
                round_trip_cost_bps=(round_trip_cost_bps),
            )

            results.append(
                {
                    "direction": direction,
                    "lower_probability": float(lower),
                    "upper_probability": float(upper),
                    "raw_prediction_count": int(np.sum(bucket_mask)),
                    **metrics,
                }
            )

    return results
