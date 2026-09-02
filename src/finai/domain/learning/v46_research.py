from __future__ import annotations

import hashlib
import json
import math
from statistics import mean, pstdev
from typing import Any


HORIZONS = (
    5,
    15,
    30,
    60,
)

META_THRESHOLD_GRID = (
    0.50,
    0.525,
    0.55,
    0.575,
    0.60,
    0.625,
    0.65,
    0.675,
    0.70,
    0.725,
    0.75,
)


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
    trials = max(
        2,
        int(trial_count),
    )
    penalty = (
        sigma
        * math.sqrt(
            2.0 * math.log(trials)
        )
        / math.sqrt(
            max(
                1,
                len(fold_returns),
            )
        )
    )
    return {
        "mean_fold_return": mu,
        "fold_std": sigma,
        "selection_penalty": float(
            penalty
        ),
        "penalized_mean_fold_return": float(
            mu - penalty
        ),
    }


def candidate_hash(
    candidate: dict[str, Any],
) -> str:
    canonical = json.dumps(
        candidate,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()
