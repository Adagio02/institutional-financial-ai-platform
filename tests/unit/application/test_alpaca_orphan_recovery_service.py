from types import SimpleNamespace
from uuid import uuid4

from finai.application.services.alpaca_orphan_recovery_service import (
    AlpacaOrphanRecoveryService,
)
from finai.domain.execution.enums import (
    OrderStatus,
)
from finai.infrastructure.execution.alpaca_broker import (
    AlpacaOrderSnapshot,
)


class FakeRepository:
    def __init__(
        self,
        *,
        order=None,
    ) -> None:
        self.order = order

        self.attached = []

    def get_by_broker_order_id(
        self,
        broker_order_id: str,
    ):
        del broker_order_id

        return None

    def get_by_id(
        self,
        order_id,
    ):
        if (
            self.order is not None
            and self.order.id
            == order_id
        ):
            return self.order

        return None

    def list_by_client_order_id(
        self,
        client_order_id: str,
    ):
        if (
            self.order is not None
            and (
                self.order.client_order_id
                == client_order_id
            )
        ):
            return [
                self.order
            ]

        return []

    def attach_broker_identity(
        self,
        order,
        *,
        broker_order_id: str,
        broker_name: str,
    ):
        order.broker_order_id = (
            broker_order_id
        )

        order.broker_name = (
            broker_name
        )

        self.attached.append(
            order.id
        )

        return order


class FakeAuditRepository:
    def __init__(
        self,
    ) -> None:
        self.events = []

    def create(
        self,
        **kwargs,
    ):
        self.events.append(
            kwargs
        )


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


class FakeBroker:
    name = "alpaca-paper"


def make_order(
    *,
    client_order_id: str | None,
):
    return SimpleNamespace(
        id=uuid4(),
        account_id=uuid4(),
        client_order_id=(
            client_order_id
        ),
        broker_order_id=None,
        broker_name=None,
        symbol="AAPL",
        side="buy",
        order_type="market",
        time_in_force="day",
        quantity=1.0,
    )


def make_snapshot(
    *,
    client_order_id: str,
    symbol: str = "AAPL",
    quantity: float = 1.0,
):
    return AlpacaOrderSnapshot(
        broker_order_id=str(
            uuid4()
        ),
        status=(
            OrderStatus.ACCEPTED
        ),
        requested_quantity=(
            quantity
        ),
        filled_quantity=0.0,
        average_fill_price=None,
        client_order_id=(
            client_order_id
        ),
        symbol=symbol,
        raw_status="accepted",
        side="buy",
        order_type="market",
        time_in_force="day",
    )


def build_service(
    *,
    order,
):
    service = (
        AlpacaOrphanRecoveryService(
            session=SimpleNamespace(),
            broker=FakeBroker(),
            execution_service=(
                FakeExecutionService()
            ),
            require_symbol_match=True,
            require_quantity_match=True,
        )
    )

    repository = (
        FakeRepository(
            order=order
        )
    )

    audit = (
        FakeAuditRepository()
    )

    execution = (
        FakeExecutionService()
    )

    service._repository = (
        repository
    )

    service._audit_repository = (
        audit
    )

    service._execution_service = (
        execution
    )

    return (
        service,
        repository,
        audit,
        execution,
    )


def test_exact_client_id_recovers() -> None:
    client_order_id = (
        "v24-test-"
        + uuid4().hex
    )

    order = make_order(
        client_order_id=(
            client_order_id
        )
    )

    snapshot = make_snapshot(
        client_order_id=(
            client_order_id
        )
    )

    (
        service,
        repository,
        audit,
        execution,
    ) = build_service(
        order=order
    )

    result = service.recover(
        snapshot=snapshot
    )

    assert result.recovered is True

    assert result.order_id == order.id

    assert repository.attached == [
        order.id
    ]

    assert len(
        audit.events
    ) == 1

    assert (
        execution.synced[0][2]
        == "orphan_recovery"
    )


def test_finai_uuid_client_id_recovers() -> None:
    order = make_order(
        client_order_id=None
    )

    snapshot = make_snapshot(
        client_order_id=(
            f"finai-{order.id}"
        )
    )

    service, _, _, _ = (
        build_service(
            order=order
        )
    )

    result = service.recover(
        snapshot=snapshot
    )

    assert result.recovered is True

    assert result.order_id == order.id


def test_symbol_mismatch_blocks_recovery() -> None:
    client_order_id = (
        "v24-test-"
        + uuid4().hex
    )

    order = make_order(
        client_order_id=(
            client_order_id
        )
    )

    snapshot = make_snapshot(
        client_order_id=(
            client_order_id
        ),
        symbol="MSFT",
    )

    service, repository, _, _ = (
        build_service(
            order=order
        )
    )

    result = service.recover(
        snapshot=snapshot
    )

    assert result.recovered is False

    assert repository.attached == []

    assert "Symbol mismatch" in (
        result.reason
    )


def test_quantity_mismatch_blocks_recovery() -> None:
    client_order_id = (
        "v24-test-"
        + uuid4().hex
    )

    order = make_order(
        client_order_id=(
            client_order_id
        )
    )

    snapshot = make_snapshot(
        client_order_id=(
            client_order_id
        ),
        quantity=2.0,
    )

    service, repository, _, _ = (
        build_service(
            order=order
        )
    )

    result = service.recover(
        snapshot=snapshot
    )

    assert result.recovered is False

    assert repository.attached == []

    assert "Quantity mismatch" in (
        result.reason
    )


def test_unknown_client_id_is_not_recovered() -> None:
    order = make_order(
        client_order_id=(
            "local-id"
        )
    )

    snapshot = make_snapshot(
        client_order_id=(
            "different-id"
        )
    )

    service, repository, _, _ = (
        build_service(
            order=order
        )
    )

    result = service.recover(
        snapshot=snapshot
    )

    assert result.recovered is False

    assert repository.attached == []