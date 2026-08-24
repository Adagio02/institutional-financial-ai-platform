from uuid import uuid4

import pytest

from finai.domain.execution.alpaca_idempotency_guard import (
    AlpacaIdempotencyGuard,
)
from finai.domain.execution.enums import (
    OrderSide,
    OrderType,
)
from finai.infrastructure.execution.alpaca_broker import (
    AlpacaPaperBroker,
)
from finai.infrastructure.execution.alpaca_client import (
    AlpacaOrderNotFoundError,
    AlpacaTransportError,
)


class FakeClient:
    def __init__(
        self,
        *,
        existing_order=None,
        transport_failure=False,
        recovery_order=None,
    ) -> None:
        self.existing_order = (
            existing_order
        )

        self.transport_failure = (
            transport_failure
        )

        self.recovery_order = (
            recovery_order
        )

        self.lookup_count = 0
        self.submit_count = 0

    def get_order_by_client_order_id(
        self,
        *,
        client_order_id: str,
    ):
        self.lookup_count += 1

        if (
            self.existing_order
            is not None
        ):
            return self.existing_order

        if (
            self.transport_failure
            and self.submit_count > 0
            and self.recovery_order
            is not None
        ):
            return self.recovery_order

        raise AlpacaOrderNotFoundError(
            "not found"
        )

    def submit_order(
        self,
        **kwargs,
    ):
        self.submit_count += 1

        if self.transport_failure:
            raise AlpacaTransportError(
                "simulated timeout"
            )

        return make_existing_order(
            client_order_id=(
                kwargs[
                    "client_order_id"
                ]
            )
        )


def make_existing_order(
    *,
    client_order_id: str,
    symbol: str = "AAPL",
    quantity: str = "1",
) -> dict:
    return {
        "id": str(
            uuid4()
        ),
        "client_order_id": (
            client_order_id
        ),
        "symbol": symbol,
        "side": "buy",
        "type": "market",
        "qty": quantity,
        "filled_qty": "0",
        "filled_avg_price": None,
        "time_in_force": "day",
        "status": "accepted",
    }


def make_broker(
    client,
) -> AlpacaPaperBroker:
    return AlpacaPaperBroker(
        client=client,
        account_guard=None,
        market_guard=None,
        idempotency_guard=(
            AlpacaIdempotencyGuard(
                require_order_match=True
            )
        ),
        lookup_before_submit=True,
        recover_after_transport_error=True,
    )


def test_existing_order_is_returned_without_submit() -> None:
    client_order_id = (
        "v27-existing"
    )

    client = FakeClient(
        existing_order=(
            make_existing_order(
                client_order_id=(
                    client_order_id
                )
            )
        )
    )

    broker = make_broker(
        client
    )

    result = broker.submit(
        order_id=uuid4(),
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1.0,
        reference_price=250.0,
        limit_price=None,
        time_in_force="day",
        client_order_id=(
            client_order_id
        ),
    )

    assert (
        client.submit_count
        == 0
    )

    assert (
        result.requested_quantity
        == 1.0
    )


def test_new_order_is_submitted_once() -> None:
    client = FakeClient()

    broker = make_broker(
        client
    )

    broker.submit(
        order_id=uuid4(),
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1.0,
        reference_price=250.0,
        limit_price=None,
        time_in_force="day",
        client_order_id=(
            "v27-new"
        ),
    )

    assert (
        client.lookup_count
        == 1
    )

    assert (
        client.submit_count
        == 1
    )


def test_transport_failure_recovers_existing_order() -> None:
    client_order_id = (
        "v27-timeout"
    )

    recovery_order = (
        make_existing_order(
            client_order_id=(
                client_order_id
            )
        )
    )

    client = FakeClient(
        transport_failure=True,
        recovery_order=(
            recovery_order
        ),
    )

    broker = make_broker(
        client
    )

    result = broker.submit(
        order_id=uuid4(),
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1.0,
        reference_price=250.0,
        limit_price=None,
        time_in_force="day",
        client_order_id=(
            client_order_id
        ),
    )

    assert (
        client.submit_count
        == 1
    )

    assert (
        client.lookup_count
        == 2
    )

    assert (
        result.requested_quantity
        == 1.0
    )


def test_transport_failure_without_broker_order_raises() -> None:
    client = FakeClient(
        transport_failure=True,
        recovery_order=None,
    )

    broker = make_broker(
        client
    )

    with pytest.raises(
        AlpacaTransportError
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
            client_order_id=(
                "v27-no-recovery"
            ),
        )

    assert (
        client.submit_count
        == 1
    )


def test_existing_mismatched_order_is_rejected() -> None:
    client_order_id = (
        "v27-mismatch"
    )

    client = FakeClient(
        existing_order=(
            make_existing_order(
                client_order_id=(
                    client_order_id
                ),
                symbol="MSFT",
            )
        )
    )

    broker = make_broker(
        client
    )

    with pytest.raises(
        ValueError,
        match="symbol does not match",
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
            client_order_id=(
                client_order_id
            ),
        )

    assert (
        client.submit_count
        == 0
    )