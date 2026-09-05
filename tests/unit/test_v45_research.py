from __future__ import annotations

import numpy as np

from finai.domain.learning.v45_research import (
    directional_positions,
    research_eligible,
    selection_penalty,
)


def test_directional_positions_can_disable_short() -> None:
    probabilities = np.asarray(
        [
            [0.10, 0.20, 0.70],
            [0.70, 0.20, 0.10],
        ],
        dtype=float,
    )
    classes = np.asarray(
        [-1, 0, 1],
        dtype=int,
    )
    positions = directional_positions(
        probabilities=probabilities,
        classes=classes,
        threshold=0.60,
        direction="long_only",
    )
    assert positions.tolist() == [1, 0]


def test_selection_penalty_is_nonnegative() -> None:
    result = selection_penalty(
        [0.01, 0.02, -0.005, 0.015, 0.01],
        trial_count=20,
    )
    assert result["selection_penalty"] >= 0.0


def test_research_eligibility_keeps_gates() -> None:
    eligible, reasons = research_eligible(
        {
            "net_return": 0.05,
            "positive_fold_fraction": 0.8,
            "trade_count": 150,
            "penalized_mean_fold_return": 0.002,
        },
        minimum_positive_fold_fraction=0.6,
        minimum_trades=100,
    )
    assert eligible is True
    assert reasons == []
