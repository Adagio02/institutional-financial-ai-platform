import pandas as pd
import pytest

from finai.domain.risk.metrics import (
    calculate_maximum_drawdown,
    calculate_sharpe_ratio,
    calculate_value_at_risk,
)


def test_maximum_drawdown() -> None:
    equity = pd.Series(
        [
            100.0,
            110.0,
            88.0,
            95.0,
        ]
    )

    drawdown = calculate_maximum_drawdown(equity)

    assert drawdown == pytest.approx(-0.20)


def test_sharpe_ratio_returns_value() -> None:
    returns = pd.Series(
        [
            0.01,
            -0.005,
            0.02,
            0.003,
            -0.002,
        ]
    )

    result = calculate_sharpe_ratio(returns)

    assert result is not None


def test_value_at_risk_is_lower_tail() -> None:
    returns = pd.Series(
        [
            -0.10,
            -0.04,
            -0.02,
            0.00,
            0.01,
            0.02,
        ]
    )

    value_at_risk = calculate_value_at_risk(
        returns,
        confidence=0.95,
    )

    assert value_at_risk is not None
    assert value_at_risk < 0
