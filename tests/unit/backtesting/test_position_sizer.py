import pytest

from finai.infrastructure.backtesting.position_sizer import (
    calculate_position_notional,
    calculate_quantity,
)


def test_position_notional() -> None:
    result = calculate_position_notional(
        portfolio_equity=100_000.0,
        position_size_fraction=0.10,
    )

    assert result == pytest.approx(10_000.0)


def test_quantity() -> None:
    result = calculate_quantity(
        position_notional=10_000.0,
        price=100.0,
    )

    assert result == pytest.approx(100.0)
