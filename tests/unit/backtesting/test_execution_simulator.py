import pytest

from finai.domain.backtesting.enums import (
    TradeSide,
)
from finai.infrastructure.backtesting.execution_simulator import (
    apply_slippage,
    calculate_transaction_cost,
)


def test_buy_slippage_increases_price() -> None:
    price = apply_slippage(
        price=100.0,
        side=TradeSide.BUY,
        slippage_bps=10.0,
    )

    assert price == pytest.approx(100.1)


def test_sell_slippage_decreases_price() -> None:
    price = apply_slippage(
        price=100.0,
        side=TradeSide.SELL,
        slippage_bps=10.0,
    )

    assert price == pytest.approx(99.9)


def test_transaction_cost() -> None:
    cost = calculate_transaction_cost(
        notional=100_000.0,
        commission_bps=1.0,
    )

    assert cost == pytest.approx(10.0)
