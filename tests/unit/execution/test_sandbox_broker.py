from uuid import uuid4

import pytest

from finai.domain.execution.enums import (
    OrderSide,
    OrderStatus,
    OrderType,
)
from finai.infrastructure.execution.sandbox_broker import (
    SandboxBroker,
)


def test_sandbox_broker_can_partial_fill() -> None:
    broker = SandboxBroker(
        commission_bps=1.0,
        slippage_bps=0.0,
        partial_fill_enabled=True,
        initial_fill_fraction=0.50,
    )

    result = broker.submit(
        order_id=uuid4(),
        symbol="TEST",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=10.0,
        reference_price=100.0,
        limit_price=None,
    )

    assert result.status == OrderStatus.PARTIALLY_FILLED

    assert result.filled_quantity == pytest.approx(5.0)

    assert len(result.fills) == 1


def test_sandbox_broker_full_fill() -> None:
    broker = SandboxBroker(
        commission_bps=1.0,
        slippage_bps=0.0,
        partial_fill_enabled=False,
        initial_fill_fraction=1.0,
    )

    result = broker.submit(
        order_id=uuid4(),
        symbol="TEST",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=10.0,
        reference_price=100.0,
        limit_price=None,
    )

    assert result.status == OrderStatus.FILLED

    assert result.filled_quantity == pytest.approx(10.0)


def test_limit_buy_can_remain_open() -> None:
    broker = SandboxBroker(
        commission_bps=0.0,
        slippage_bps=0.0,
        partial_fill_enabled=False,
        initial_fill_fraction=1.0,
    )

    result = broker.submit(
        order_id=uuid4(),
        symbol="TEST",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=10.0,
        reference_price=101.0,
        limit_price=100.0,
    )

    assert result.status == OrderStatus.ACCEPTED

    assert result.filled_quantity == 0.0
    assert result.fills == ()
