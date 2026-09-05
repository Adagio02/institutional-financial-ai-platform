from __future__ import annotations

import numpy as np

from finai.application.services.v431_learning_service import (
    V431LearningService,
)
from finai.domain.learning.v43_research import (
    BUY,
    HOLD,
    SELL,
)


def create_service() -> V431LearningService:
    service = object.__new__(V431LearningService)

    service._forward_horizon_bars = 15
    service._v41_round_trip_cost_bps = 2.0
    service._minimum_trades = 2

    service._long_probability_thresholds = (
        0.50,
        0.55,
        0.60,
    )

    service._short_probability_thresholds = (
        0.50,
        0.55,
        0.60,
    )

    return service


def test_long_direction_can_trade_independently() -> None:
    service = create_service()

    probabilities = np.asarray(
        [
            [0.10, 0.20, 0.70],
            [0.15, 0.20, 0.65],
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

    positions = service._direction_positions(
        probabilities=probabilities,
        classes=classes,
        direction="long",
        threshold=0.60,
    )

    assert positions.tolist() == [
        BUY,
        BUY,
    ]


def test_short_direction_can_trade_independently() -> None:
    service = create_service()

    probabilities = np.asarray(
        [
            [0.70, 0.20, 0.10],
            [0.65, 0.20, 0.15],
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

    positions = service._direction_positions(
        probabilities=probabilities,
        classes=classes,
        direction="short",
        threshold=0.60,
    )

    assert positions.tolist() == [
        SELL,
        SELL,
    ]


def test_hold_blocks_direction() -> None:
    service = create_service()

    probabilities = np.asarray(
        [
            [
                0.10,
                0.60,
                0.55,
            ]
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

    positions = service._direction_positions(
        probabilities=probabilities,
        classes=classes,
        direction="long",
        threshold=0.50,
    )

    assert positions.tolist() == [
        HOLD,
    ]


def test_disabled_short_threshold_blocks_short() -> None:
    probabilities = np.asarray(
        [
            [
                0.95,
                0.03,
                0.02,
            ]
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

    positions = V431LearningService.positions_from_probabilities(
        probabilities=probabilities,
        classes=classes,
        long_threshold=0.60,
        short_threshold=1.0,
    )

    assert positions.tolist() == [
        HOLD,
    ]


def test_long_enabled_short_disabled_policy() -> None:
    probabilities = np.asarray(
        [
            [
                0.10,
                0.20,
                0.70,
            ],
            [
                0.80,
                0.10,
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

    positions = V431LearningService.positions_from_probabilities(
        probabilities=probabilities,
        classes=classes,
        long_threshold=0.60,
        short_threshold=1.0,
    )

    assert positions.tolist() == [
        BUY,
        HOLD,
    ]


def test_both_directions_can_be_disabled() -> None:
    probabilities = np.asarray(
        [
            [
                0.80,
                0.10,
                0.10,
            ],
            [
                0.10,
                0.10,
                0.80,
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

    positions = V431LearningService.positions_from_probabilities(
        probabilities=probabilities,
        classes=classes,
        long_threshold=1.0,
        short_threshold=1.0,
    )

    assert positions.tolist() == [
        HOLD,
        HOLD,
    ]


def test_threshold_grid_still_has_probability_floor() -> None:
    service = create_service()

    thresholds = service._candidate_thresholds()

    assert min(thresholds) >= 0.50
