import pytest

from finai.domain.execution.enums import (
    OrderSide,
)
from finai.infrastructure.execution.execution_price import (
    apply_execution_slippage,
    calculate_commission,
)


def test_buy_execution_slippage() -> None:
    result = apply_execution_slippage(
        reference_price=100.0,
        side=OrderSide.BUY,
        slippage_bps=10.0,
    )

    assert result == pytest.approx(100.1)


def test_sell_execution_slippage() -> None:
    result = apply_execution_slippage(
        reference_price=100.0,
        side=OrderSide.SELL,
        slippage_bps=10.0,
    )

    assert result == pytest.approx(99.9)


def test_commission() -> None:
    result = calculate_commission(
        notional=10_000.0,
        commission_bps=1.0,
    )

    assert result == pytest.approx(1.0)
