from types import SimpleNamespace
from uuid import uuid4

from finai.application.services.alpaca_order_discovery_service import (
    AlpacaOrderDiscoveryService,
)
from finai.domain.execution.enums import (
    OrderStatus,
)
from finai.infrastructure.execution.alpaca_broker import (
    AlpacaOrderSnapshot,
)


class FakeSession:
    pass


class FakeBroker:
    name = "alpaca-paper"

    def __init__(
        self,
        *,
        all_orders,
        open_orders,
    ) -> None:
        self._all_orders = (
            all_orders
        )

        self._open_orders = (
            open_orders
        )

    def list_snapshots(
        self,
        *,
        status: str,
        limit: int,
        direction: str,
    ):
        assert (
            direction
            in {
                "asc",
                "desc",
            }
        )

        if status == "all":
            return (
                self._all_orders[
                    :limit
                ]
            )

        if status == "open":
            return (
                self._open_orders[
                    :limit
                ]
            )

        raise AssertionError(
            "Unexpected status."
        )


class FakeRepository:
    def __init__(
        self,
        *,
        all_orders,
        open_orders,
    ) -> None:
        self.all_orders = (
            all_orders
        )

        self.open_orders = (
            open_orders
        )

        self.touched = []

    def list_for_broker(
        self,
        *,
        broker_name: str,
        limit: int,
    ):
        assert (
            broker_name
            == "alpaca-paper"
        )

        return self.all_orders[
            :limit
        ]

    def list_open_for_broker(
        self,
        *,
        broker_name: str,
        limit: int,
    ):
        assert (
            broker_name
            == "alpaca-paper"
        )

        return self.open_orders[
            :limit
        ]

    def touch_synced(
        self,
        order,
    ):
        self.touched.append(
            order.id
        )

        return order


class FakeExecutionService:
    def __init__(
        self,
    ) -> None:
        self.synced = []

    def sync_from_snapshot(
        self,
        *,
        order,
        snapshot,
        source: str,
    ):
        self.synced.append(
            (
                order.id,
                snapshot
                .broker_order_id,
                source,
            )
        )

        return order


def make_snapshot(
    *,
    broker_order_id: str,
    status: OrderStatus,
    filled_quantity: float = 0.0,
    average_fill_price: (
        float | None
    ) = None,
) -> AlpacaOrderSnapshot:
    return AlpacaOrderSnapshot(
        broker_order_id=(
            broker_order_id
        ),
        status=status,
        requested_quantity=1.0,
        filled_quantity=(
            filled_quantity
        ),
        average_fill_price=(
            average_fill_price
        ),
        client_order_id=(
            f"client-{broker_order_id}"
        ),
        symbol="AAPL",
        raw_status=(
            status.value
        ),
    )


def make_order(
    *,
    broker_order_id: str,
    status: OrderStatus,
    filled_quantity: float = 0.0,
    average_fill_price=None,
):
    return SimpleNamespace(
        id=uuid4(),
        broker_order_id=(
            broker_order_id
        ),
        status=status.value,
        filled_quantity=(
            filled_quantity
        ),
        average_fill_price=(
            average_fill_price
        ),
    )


def build_service(
    *,
    broker,
    repository,
    execution,
    limit: int = 100,
):
    service = (
        AlpacaOrderDiscoveryService(
            session=FakeSession(),
            broker=broker,
            execution_service=(
                execution
            ),
            limit=limit,
            direction="desc",
        )
    )

    service._repository = (
        repository
    )

    return service


def test_matching_stable_order_is_refreshed() -> None:
    broker_id = str(
        uuid4()
    )

    local = make_order(
        broker_order_id=(
            broker_id
        ),
        status=(
            OrderStatus.ACCEPTED
        ),
    )

    snapshot = make_snapshot(
        broker_order_id=(
            broker_id
        ),
        status=(
            OrderStatus.ACCEPTED
        ),
    )

    repository = FakeRepository(
        all_orders=[
            local
        ],
        open_orders=[
            local
        ],
    )

    execution = (
        FakeExecutionService()
    )

    service = build_service(
        broker=FakeBroker(
            all_orders=[
                snapshot
            ],
            open_orders=[
                snapshot
            ],
        ),
        repository=repository,
        execution=execution,
    )

    result = (
        service.discover()
    )

    assert result.matched == 1

    assert (
        result.refreshed
        == 1
    )

    assert (
        result.synchronized
        == 0
    )

    assert (
        repository.touched
        == [
            local.id
        ]
    )


def test_drifted_order_is_synchronized() -> None:
    broker_id = str(
        uuid4()
    )

    local = make_order(
        broker_order_id=(
            broker_id
        ),
        status=(
            OrderStatus.ACCEPTED
        ),
        filled_quantity=0.0,
    )

    snapshot = make_snapshot(
        broker_order_id=(
            broker_id
        ),
        status=(
            OrderStatus.FILLED
        ),
        filled_quantity=1.0,
        average_fill_price=250.0,
    )

    repository = FakeRepository(
        all_orders=[
            local
        ],
        open_orders=[
            local
        ],
    )

    execution = (
        FakeExecutionService()
    )

    service = build_service(
        broker=FakeBroker(
            all_orders=[
                snapshot
            ],
            open_orders=[],
        ),
        repository=repository,
        execution=execution,
    )

    result = (
        service.discover()
    )

    assert (
        result.synchronized
        == 1
    )

    assert (
        len(execution.synced)
        == 1
    )

    assert (
        execution.synced[0][2]
        == "broker_discovery"
    )


def test_broker_only_order_is_reported() -> None:
    snapshot = make_snapshot(
        broker_order_id=str(
            uuid4()
        ),
        status=(
            OrderStatus.ACCEPTED
        ),
    )

    repository = FakeRepository(
        all_orders=[],
        open_orders=[],
    )

    service = build_service(
        broker=FakeBroker(
            all_orders=[
                snapshot
            ],
            open_orders=[
                snapshot
            ],
        ),
        repository=repository,
        execution=(
            FakeExecutionService()
        ),
    )

    result = (
        service.discover()
    )

    assert (
        len(result.broker_only)
        == 1
    )

    assert result.matched == 0


def test_local_open_missing_remote_is_reported() -> None:
    local = make_order(
        broker_order_id=str(
            uuid4()
        ),
        status=(
            OrderStatus.ACCEPTED
        ),
    )

    repository = FakeRepository(
        all_orders=[
            local
        ],
        open_orders=[
            local
        ],
    )

    service = build_service(
        broker=FakeBroker(
            all_orders=[],
            open_orders=[],
        ),
        repository=repository,
        execution=(
            FakeExecutionService()
        ),
    )

    result = (
        service.discover()
    )

    assert (
        result
        .local_open_missing_remote
        == (
            local.id,
        )
    )


def test_truncated_remote_open_list_suppresses_missing_report() -> None:
    local = make_order(
        broker_order_id=str(
            uuid4()
        ),
        status=(
            OrderStatus.ACCEPTED
        ),
    )

    remote = [
        make_snapshot(
            broker_order_id=str(
                uuid4()
            ),
            status=(
                OrderStatus.ACCEPTED
            ),
        )
    ]

    repository = FakeRepository(
        all_orders=[
            local
        ],
        open_orders=[
            local
        ],
    )

    service = build_service(
        broker=FakeBroker(
            all_orders=remote,
            open_orders=remote,
        ),
        repository=repository,
        execution=(
            FakeExecutionService()
        ),
        limit=1,
    )

    result = (
        service.discover()
    )

    assert (
        result
        .remote_open_truncated
        is True
    )

    assert (
        result
        .local_open_missing_remote
        == ()
    )