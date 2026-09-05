import numpy as np

from finai.domain.learning.v33_thresholds import (
    evaluate_positions,
    probabilities_to_positions,
)


def test_high_long_probability_creates_long() -> None:
    probabilities = np.array(
        [
            [
                0.10,
                0.20,
                0.70,
            ],
        ]
    )

    classes = np.array(
        [
            -1,
            0,
            1,
        ]
    )

    positions = probabilities_to_positions(
        probabilities=probabilities,
        classes=classes,
        long_threshold=0.60,
        short_threshold=0.60,
    )

    assert positions.tolist() == [
        1.0
    ]


def test_high_short_probability_creates_short() -> None:
    probabilities = np.array(
        [
            [
                0.70,
                0.20,
                0.10,
            ],
        ]
    )

    classes = np.array(
        [
            -1,
            0,
            1,
        ]
    )

    positions = probabilities_to_positions(
        probabilities=probabilities,
        classes=classes,
        long_threshold=0.60,
        short_threshold=0.60,
    )

    assert positions.tolist() == [
        -1.0
    ]


def test_low_confidence_stays_flat() -> None:
    probabilities = np.array(
        [
            [
                0.34,
                0.33,
                0.33,
            ],
        ]
    )

    classes = np.array(
        [
            -1,
            0,
            1,
        ]
    )

    positions = probabilities_to_positions(
        probabilities=probabilities,
        classes=classes,
        long_threshold=0.60,
        short_threshold=0.60,
    )

    assert positions.tolist() == [
        0.0
    ]


def test_profitable_positions_produce_positive_return() -> None:
    positions = np.array(
        [
            1.0,
            1.0,
            0.0,
        ]
    )

    returns = np.array(
        [
            0.01,
            0.01,
            0.0,
        ]
    )

    (
        net_return,
        trade_count,
        turnover,
        maximum_drawdown,
    ) = evaluate_positions(
        positions=positions,
        forward_returns=returns,
        round_trip_cost_bps=0.0,
    )

    assert net_return > 0.0
    assert trade_count == 2
    assert turnover == 2.0
    assert maximum_drawdown >= 0.0