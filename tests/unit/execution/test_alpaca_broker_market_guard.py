from uuid import uuid4

import pytest

from finai.domain.execution.alpaca_market_guard import (
    AlpacaMarketGuard,
)
from finai.domain.execution.enums import (
    OrderSide,
    OrderType,
)
from finai.infrastructure.execution.alpaca_broker import (
    AlpacaPaperBroker,
)


class FakeClient:
    def __init__(
        self,
        *,
        asset: dict,
        clock: dict,
    ) -> None:
        self._asset = asset

        self._clock = clock

        self.submit_count = 0

    def get_asset(
        self,
        *,
        symbol: str,
    ):
        assert symbol == "AAPL"

        return self._asset

    def get_clock(
        self,
    ):
        return self._clock

    def submit_order(
        self,
        **kwargs,
    ):
        self.submit_count += 1

        return {
            "id": str(
                uuid4()
            ),
            "status": "accepted",
            "qty": str(
                kwargs["quantity"]
            ),
            "filled_qty": "0",
            "filled_avg_price": None,
            "client_order_id": (
                kwargs[
                    "client_order_id"
                ]
            ),
            "symbol": (
                kwargs["symbol"]
            ),
            "side": (
                kwargs["side"]
            ),
            "type": (
                kwargs["order_type"]
            ),
            "time_in_force": (
                kwargs[
                    "time_in_force"
                ]
            ),
        }


def make_guard(
) -> AlpacaMarketGuard:
    return AlpacaMarketGuard(
        require_active_asset=True,
        require_tradable_asset=True,
        require_market_open=True,
        require_fractionable=True,
    )


def make_asset(
    *,
    tradable: bool = True,
) -> dict:
    return {
        "symbol": "AAPL",
        "status": "active",
        "tradable": tradable,
        "fractionable": True,
    }


def make_clock(
    *,
    is_open: bool = True,
) -> dict:
    return {
        "timestamp": (
            "2026-08-24T10:30:00-04:00"
        ),
        "is_open": is_open,
        "next_open": (
            "2026-08-25T09:30:00-04:00"
        ),
        "next_close": (
            "2026-08-24T16:00:00-04:00"
        ),
    }


def test_submission_occurs_when_market_guard_passes() -> None:
    client = FakeClient(
        asset=make_asset(),
        clock=make_clock(),
    )

    broker = AlpacaPaperBroker(
        client=client,
        market_guard=(
            make_guard()
        ),
    )

    result = broker.submit(
        order_id=uuid4(),
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=(
            OrderType.MARKET
        ),
        quantity=1.0,
        reference_price=250.0,
        limit_price=None,
        time_in_force="day",
    )

    assert (
        client.submit_count
        == 1
    )

    assert (
        result.filled_quantity
        == 0.0
    )


def test_closed_market_prevents_submission() -> None:
    client = FakeClient(
        asset=make_asset(),
        clock=make_clock(
            is_open=False
        ),
    )

    broker = AlpacaPaperBroker(
        client=client,
        market_guard=(
            make_guard()
        ),
    )

    with pytest.raises(
        ValueError,
        match="market is closed",
    ):
        broker.submit(
            order_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=(
                OrderType.MARKET
            ),
            quantity=1.0,
            reference_price=250.0,
            limit_price=None,
            time_in_force="day",
        )

    assert (
        client.submit_count
        == 0
    )


def test_non_tradable_asset_prevents_submission() -> None:
    client = FakeClient(
        asset=make_asset(
            tradable=False
        ),
        clock=make_clock(),
    )

    broker = AlpacaPaperBroker(
        client=client,
        market_guard=(
            make_guard()
        ),
    )

    with pytest.raises(
        ValueError,
        match="not tradable",
    ):
        broker.submit(
            order_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=(
                OrderType.MARKET
            ),
            quantity=1.0,
            reference_price=250.0,
            limit_price=None,
            time_in_force="day",
        )

    assert (
        client.submit_count
        == 0
    )