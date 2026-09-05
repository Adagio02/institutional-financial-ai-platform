from uuid import uuid4

import pytest

from finai.domain.execution.alpaca_account_guard import (
    AlpacaAccountGuard,
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
        account: dict,
    ) -> None:
        self.account_data = account

        self.submit_count = 0

    def get_account(
        self,
    ):
        return self.account_data

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
                kwargs["time_in_force"]
            ),
        }


def make_guard(
) -> AlpacaAccountGuard:
    return AlpacaAccountGuard(
        require_active=True,
        maximum_buying_power_fraction=0.10,
        require_positive_buying_power=True,
    )


def make_active_account(
    *,
    buying_power: str = "100000",
) -> dict:
    return {
        "status": "ACTIVE",
        "trading_blocked": False,
        "account_blocked": False,
        "buying_power": (
            buying_power
        ),
        "cash": "50000",
        "equity": "100000",
    }


def test_broker_submits_after_guard_passes() -> None:
    client = FakeClient(
        account=(
            make_active_account()
        )
    )

    broker = AlpacaPaperBroker(
        client=client,
        account_guard=(
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

    assert client.submit_count == 1

    assert (
        result.filled_quantity
        == 0.0
    )


def test_blocked_account_never_submits() -> None:
    account = (
        make_active_account()
    )

    account[
        "trading_blocked"
    ] = True

    client = FakeClient(
        account=account
    )

    broker = AlpacaPaperBroker(
        client=client,
        account_guard=(
            make_guard()
        ),
    )

    with pytest.raises(
        ValueError,
        match="blocked trading",
    ):
        broker.submit(
            order_id=uuid4(),
            symbol="AAPL",
            side=(
                OrderSide.BUY
            ),
            order_type=(
                OrderType.MARKET
            ),
            quantity=1.0,
            reference_price=250.0,
            limit_price=None,
            time_in_force="day",
        )

    assert client.submit_count == 0


def test_oversized_buy_never_submits() -> None:
    client = FakeClient(
        account=(
            make_active_account(
                buying_power="1000"
            )
        )
    )

    broker = AlpacaPaperBroker(
        client=client,
        account_guard=(
            make_guard()
        ),
    )

    with pytest.raises(
        ValueError,
        match="buying-power guard",
    ):
        broker.submit(
            order_id=uuid4(),
            symbol="AAPL",
            side=(
                OrderSide.BUY
            ),
            order_type=(
                OrderType.MARKET
            ),
            quantity=1.0,
            reference_price=250.0,
            limit_price=None,
            time_in_force="day",
        )

    assert client.submit_count == 0


def test_guard_can_be_disabled_at_broker_level() -> None:
    account = (
        make_active_account(
            buying_power="0"
        )
    )

    client = FakeClient(
        account=account
    )

    broker = AlpacaPaperBroker(
        client=client,
        account_guard=None,
    )

    broker.submit(
        order_id=uuid4(),
        symbol="AAPL",
        side=(
            OrderSide.BUY
        ),
        order_type=(
            OrderType.MARKET
        ),
        quantity=1.0,
        reference_price=250.0,
        limit_price=None,
        time_in_force="day",
    )

    assert client.submit_count == 1