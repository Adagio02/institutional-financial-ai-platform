import pytest

from finai.domain.execution.position_accounting import (
    apply_fill_to_position,
)


def test_open_long_position() -> None:
    result = apply_fill_to_position(
        current_quantity=0.0,
        current_average_price=0.0,
        fill_quantity=10.0,
        fill_price=100.0,
    )

    assert result.quantity == 10.0

    assert result.average_price == pytest.approx(100.0)

    assert result.realized_pnl_delta == pytest.approx(0.0)


def test_add_to_long_position() -> None:
    result = apply_fill_to_position(
        current_quantity=10.0,
        current_average_price=100.0,
        fill_quantity=10.0,
        fill_price=120.0,
    )

    assert result.quantity == 20.0

    assert result.average_price == pytest.approx(110.0)


def test_reduce_long_realizes_profit() -> None:
    result = apply_fill_to_position(
        current_quantity=10.0,
        current_average_price=100.0,
        fill_quantity=-4.0,
        fill_price=125.0,
    )

    assert result.quantity == 6.0

    assert result.average_price == pytest.approx(100.0)

    assert result.realized_pnl_delta == pytest.approx(100.0)


def test_close_long_position() -> None:
    result = apply_fill_to_position(
        current_quantity=10.0,
        current_average_price=100.0,
        fill_quantity=-10.0,
        fill_price=90.0,
    )

    assert result.quantity == 0.0
    assert result.average_price == 0.0

    assert result.realized_pnl_delta == pytest.approx(-100.0)


def test_flip_long_to_short() -> None:
    result = apply_fill_to_position(
        current_quantity=10.0,
        current_average_price=100.0,
        fill_quantity=-15.0,
        fill_price=110.0,
    )

    assert result.quantity == -5.0

    assert result.average_price == pytest.approx(110.0)

    assert result.realized_pnl_delta == pytest.approx(100.0)


def test_reduce_short_realizes_profit() -> None:
    result = apply_fill_to_position(
        current_quantity=-10.0,
        current_average_price=100.0,
        fill_quantity=4.0,
        fill_price=80.0,
    )

    assert result.quantity == -6.0

    assert result.average_price == pytest.approx(100.0)

    assert result.realized_pnl_delta == pytest.approx(80.0)
