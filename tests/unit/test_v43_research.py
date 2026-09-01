from __future__ import annotations

import numpy as np
import pytest

from finai.application.services.v43_learning_service import (
    V43LearningService,
)
from finai.domain.learning.v43_research import (
    BUY,
    HOLD,
    SELL,
    event_trade_returns,
    probability_columns,
    select_non_overlapping_indices,
)


def test_hold_probability_blocks_long_trade() -> None:
    probabilities = np.asarray(
        [
            [
                0.10,
                0.50,
                0.40,
            ],
        ],
        dtype=float,
    )

    classes = np.asarray(
        [
            SELL,
            HOLD,
            BUY,
        ],
        dtype=int,
    )

    positions = V43LearningService.positions_from_probabilities(
        probabilities=probabilities,
        classes=classes,
        long_threshold=0.40,
        short_threshold=0.40,
    )

    assert positions.tolist() == [
        HOLD,
    ]


def test_long_must_exceed_probability_floor() -> None:
    probabilities = np.asarray(
        [
            [
                0.10,
                0.41,
                0.49,
            ],
        ],
        dtype=float,
    )

    classes = np.asarray(
        [
            SELL,
            HOLD,
            BUY,
        ],
        dtype=int,
    )

    positions = V43LearningService.positions_from_probabilities(
        probabilities=probabilities,
        classes=classes,
        long_threshold=0.36,
        short_threshold=0.36,
    )

    assert positions.tolist() == [
        HOLD,
    ]


def test_strong_long_signal_is_allowed() -> None:
    probabilities = np.asarray(
        [
            [
                0.10,
                0.25,
                0.65,
            ],
        ],
        dtype=float,
    )

    classes = np.asarray(
        [
            SELL,
            HOLD,
            BUY,
        ],
        dtype=int,
    )

    positions = V43LearningService.positions_from_probabilities(
        probabilities=probabilities,
        classes=classes,
        long_threshold=0.60,
        short_threshold=0.60,
    )

    assert positions.tolist() == [
        BUY,
    ]


def test_strong_short_signal_is_allowed() -> None:
    probabilities = np.asarray(
        [
            [
                0.70,
                0.20,
                0.10,
            ],
        ],
        dtype=float,
    )

    classes = np.asarray(
        [
            SELL,
            HOLD,
            BUY,
        ],
        dtype=int,
    )

    positions = V43LearningService.positions_from_probabilities(
        probabilities=probabilities,
        classes=classes,
        long_threshold=0.60,
        short_threshold=0.60,
    )

    assert positions.tolist() == [
        SELL,
    ]


def test_probability_columns_follow_class_labels() -> None:
    probabilities = np.asarray(
        [
            [
                0.20,
                0.30,
                0.50,
            ],
        ],
        dtype=float,
    )

    classes = np.asarray(
        [
            BUY,
            SELL,
            HOLD,
        ],
        dtype=int,
    )

    (
        short_probability,
        hold_probability,
        long_probability,
    ) = probability_columns(
        probabilities=probabilities,
        classes=classes,
    )

    assert short_probability[0] == pytest.approx(0.30)

    assert hold_probability[0] == pytest.approx(0.50)

    assert long_probability[0] == pytest.approx(0.20)


def test_non_overlapping_event_selection() -> None:
    eligible = np.ones(
        31,
        dtype=bool,
    )

    selected = select_non_overlapping_indices(
        eligible=eligible,
        horizon=15,
    )

    assert selected.tolist() == [
        0,
        15,
        30,
    ]


def test_event_trade_cost_is_round_trip_once() -> None:
    positions = np.asarray(
        [
            BUY,
        ],
        dtype=int,
    )

    forward_returns = np.asarray(
        [
            0.01,
        ],
        dtype=float,
    )

    trades = event_trade_returns(
        positions=positions,
        forward_returns=(forward_returns),
        horizon=15,
        round_trip_cost_bps=2.0,
    )

    assert len(trades) == 1

    assert trades[0] == pytest.approx(0.0098)


def test_event_short_profit_direction() -> None:
    positions = np.asarray(
        [
            SELL,
        ],
        dtype=int,
    )

    forward_returns = np.asarray(
        [
            -0.02,
        ],
        dtype=float,
    )

    trades = event_trade_returns(
        positions=positions,
        forward_returns=(forward_returns),
        horizon=15,
        round_trip_cost_bps=0.0,
    )

    assert trades[0] == pytest.approx(0.02)


def test_threshold_grid_never_goes_below_half() -> None:
    service = object.__new__(V43LearningService)

    service._long_probability_thresholds = (
        0.36,
        0.40,
        0.44,
        0.48,
        0.52,
        0.56,
    )

    service._short_probability_thresholds = (
        0.36,
        0.40,
        0.44,
        0.48,
        0.52,
        0.56,
    )

    thresholds = service._candidate_thresholds()

    assert min(thresholds) >= 0.50

    assert 0.70 in thresholds

    assert 0.80 in thresholds
