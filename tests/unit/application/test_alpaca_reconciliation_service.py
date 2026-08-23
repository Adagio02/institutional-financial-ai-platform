from types import SimpleNamespace
from uuid import uuid4

from finai.application.services.alpaca_reconciliation_service import (
    AlpacaReconciliationService,
)


class FakeSession:
    def __init__(
        self,
    ) -> None:
        self.rollback_count = 0

    def rollback(
        self,
    ) -> None:
        self.rollback_count += 1


class FakeRepository:
    def __init__(
        self,
        orders,
    ) -> None:
        self.orders = orders

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

        return self.orders[
            :limit
        ]


class FakeExecutionService:
    def __init__(
        self,
        *,
        fail_order_id=None,
    ) -> None:
        self.synced = []

        self.fail_order_id = (
            fail_order_id
        )

    def sync(
        self,
        *,
        order,
    ):
        if (
            order.id
            == self.fail_order_id
        ):
            raise RuntimeError(
                "sync failed"
            )

        self.synced.append(
            order.id
        )

        return order


def make_order():
    return SimpleNamespace(
        id=uuid4(),
        broker_order_id=str(
            uuid4()
        ),
    )


def test_reconcile_success() -> None:
    session = FakeSession()

    orders = [
        make_order(),
        make_order(),
    ]

    execution = (
        FakeExecutionService()
    )

    service = (
        AlpacaReconciliationService(
            session=session,
            execution_service=(
                execution
            ),
            batch_size=100,
        )
    )

    service._repository = (
        FakeRepository(
            orders
        )
    )

    result = (
        service
        .reconcile_open_orders()
    )

    assert result.scanned == 2

    assert (
        result.synchronized
        == 2
    )

    assert result.failed == 0

    assert (
        session.rollback_count
        == 0
    )


def test_reconcile_failure_isolated() -> None:
    session = FakeSession()

    first = make_order()

    second = make_order()

    execution = (
        FakeExecutionService(
            fail_order_id=(
                first.id
            )
        )
    )

    service = (
        AlpacaReconciliationService(
            session=session,
            execution_service=(
                execution
            ),
            batch_size=100,
        )
    )

    service._repository = (
        FakeRepository(
            [
                first,
                second,
            ]
        )
    )

    result = (
        service
        .reconcile_open_orders()
    )

    assert result.scanned == 2

    assert (
        result.synchronized
        == 1
    )

    assert result.failed == 1

    assert (
        session.rollback_count
        == 1
    )

    assert (
        len(result.failures)
        == 1
    )

    assert (
        result.failures[0]
        .order_id
        == first.id
    )