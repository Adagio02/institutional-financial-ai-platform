import pytest

from finai.domain.execution.enums import (
    OrderSide,
    OrderType,
)
from finai.infrastructure.execution.paper_broker import (
    PaperBroker,
)


def test_market_order_fills() -> None:
    broker = PaperBroker(
        commission_bps=1.0,
        slippage_bps=2.0,
    )

    fill = broker.execute(
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=10,
        reference_price=100.0,
        limit_price=None,
    )

    assert fill is not None
    assert fill.quantity == 10
    assert fill.price > 100.0
    assert fill.commission > 0


def test_buy_limit_does_not_fill_above_limit() -> None:
    broker = PaperBroker(
        commission_bps=0.0,
        slippage_bps=0.0,
    )

    fill = broker.execute(
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=10,
        reference_price=101.0,
        limit_price=100.0,
    )

    assert fill is None


def test_buy_limit_fills_at_or_below_limit() -> None:
    broker = PaperBroker(
        commission_bps=0.0,
        slippage_bps=0.0,
    )

    fill = broker.execute(
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=10,
        reference_price=99.0,
        limit_price=100.0,
    )

    assert fill is not None
    assert fill.price == pytest.approx(99.0)
