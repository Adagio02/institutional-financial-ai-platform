from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from finai.application.services.v421_learning_service import (
    V421LearningService,
)
from finai.domain.learning.v421_features import (
    apply_v421_session_features,
)


def create_test_service(
    *,
    horizon: int = 15,
    round_trip_cost_bps: float = 2.0,
) -> V421LearningService:
    service = object.__new__(V421LearningService)

    service._forward_horizon_bars = horizon

    service._v41_round_trip_cost_bps = round_trip_cost_bps

    return service


def test_fixed_horizon_backtest_does_not_overlap() -> None:
    service = create_test_service(
        horizon=15,
        round_trip_cost_bps=0.0,
    )

    positions = np.ones(
        30,
        dtype=int,
    )

    forward_returns = np.full(
        30,
        0.01,
        dtype=float,
    )

    result = service.simulate(
        positions=positions,
        forward_returns=forward_returns,
    )

    # Signals at index 0 and index 15.
    assert result.trade_count == 2

    expected = (1.01**2) - 1.0

    assert result.gross_return == pytest.approx(expected)

    assert result.net_return == pytest.approx(expected)


def test_round_trip_cost_is_charged_once_per_trade() -> None:
    service = create_test_service(
        horizon=15,
        round_trip_cost_bps=2.0,
    )

    positions = np.zeros(
        15,
        dtype=int,
    )

    positions[0] = 1

    forward_returns = np.zeros(
        15,
        dtype=float,
    )

    forward_returns[0] = 0.01

    result = service.simulate(
        positions=positions,
        forward_returns=forward_returns,
    )

    assert result.trade_count == 1

    assert result.turnover == pytest.approx(2.0)

    assert result.transaction_cost == pytest.approx(0.0002)

    assert result.gross_return == pytest.approx(0.01)

    assert result.net_return == pytest.approx(0.0098)


def test_long_and_short_returns_have_correct_direction() -> None:
    service = create_test_service(
        horizon=15,
        round_trip_cost_bps=0.0,
    )

    long_result = service.simulate(
        positions=np.asarray(
            [1],
            dtype=int,
        ),
        forward_returns=np.asarray(
            [0.02],
            dtype=float,
        ),
    )

    short_result = service.simulate(
        positions=np.asarray(
            [-1],
            dtype=int,
        ),
        forward_returns=np.asarray(
            [-0.02],
            dtype=float,
        ),
    )

    assert long_result.net_return == pytest.approx(0.02)

    assert short_result.net_return == pytest.approx(0.02)


def test_winter_market_open_is_dst_aware() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": [
                "2026-01-15T14:30:00Z",
            ]
        }
    )

    result = apply_v421_session_features(frame)

    assert (
        result.loc[
            0,
            "minutes_from_open",
        ]
        == 0
    )

    assert (
        result.loc[
            0,
            "opening_session",
        ]
        == 1.0
    )


def test_summer_market_open_is_dst_aware() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": [
                "2026-07-15T13:30:00Z",
            ]
        }
    )

    result = apply_v421_session_features(frame)

    assert (
        result.loc[
            0,
            "minutes_from_open",
        ]
        == 0
    )

    assert (
        result.loc[
            0,
            "opening_session",
        ]
        == 1.0
    )


def test_market_close_is_four_pm_new_york() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": [
                "2026-01-15T21:00:00Z",
                "2026-07-15T20:00:00Z",
            ]
        }
    )

    result = apply_v421_session_features(frame)

    assert result["minutes_to_close"].tolist() == [
        0,
        0,
    ]


def test_no_signal_produces_zero_return() -> None:
    service = create_test_service(
        horizon=15,
        round_trip_cost_bps=2.0,
    )

    result = service.simulate(
        positions=np.zeros(
            100,
            dtype=int,
        ),
        forward_returns=np.full(
            100,
            0.01,
            dtype=float,
        ),
    )

    assert result.trade_count == 0
    assert result.turnover == 0.0
    assert result.gross_return == 0.0
    assert result.net_return == 0.0
    assert result.transaction_cost == 0.0
    assert result.maximum_drawdown == 0.0
