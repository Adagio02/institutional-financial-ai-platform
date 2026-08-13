import pytest

from finai.domain.strategy.sizing import (
    calculate_buy_size,
    calculate_sell_size,
)


def test_buy_size_uses_equity_and_confidence() -> None:
    result = calculate_buy_size(
        account_equity=100_000.0,
        reference_price=100.0,
        confidence=0.80,
        minimum_confidence=0.60,
        maximum_equity_fraction=0.05,
    )

    assert result.allocation_fraction == pytest.approx(0.04)

    assert result.notional == pytest.approx(4_000.0)

    assert result.quantity == pytest.approx(40.0)


def test_buy_below_confidence_returns_zero() -> None:
    result = calculate_buy_size(
        account_equity=100_000.0,
        reference_price=100.0,
        confidence=0.50,
        minimum_confidence=0.60,
        maximum_equity_fraction=0.05,
    )

    assert result.quantity == 0
    assert result.notional == 0


def test_sell_sizes_existing_position() -> None:
    result = calculate_sell_size(
        current_position_quantity=100.0,
        reference_price=100.0,
        confidence=0.75,
        minimum_confidence=0.60,
        maximum_position_fraction=1.0,
    )

    assert result.quantity == pytest.approx(75.0)

    assert result.notional == pytest.approx(7_500.0)


def test_sell_without_position_returns_zero() -> None:
    result = calculate_sell_size(
        current_position_quantity=0.0,
        reference_price=100.0,
        confidence=0.90,
        minimum_confidence=0.60,
        maximum_position_fraction=1.0,
    )

    assert result.quantity == 0
    assert result.notional == 0


def test_invalid_confidence_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="confidence",
    ):
        calculate_buy_size(
            account_equity=100_000.0,
            reference_price=100.0,
            confidence=1.20,
            minimum_confidence=0.60,
            maximum_equity_fraction=0.05,
        )
