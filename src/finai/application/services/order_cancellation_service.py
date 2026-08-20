from uuid import UUID

from sqlalchemy.orm import Session

from finai.domain.execution.enums import (
    OrderStatus,
)
from finai.infrastructure.database.repositories.execution_audit_repository import (
    ExecutionAuditRepository,
)
from finai.infrastructure.database.repositories.order_repository import (
    OrderRepository,
)
from finai.infrastructure.execution.sandbox_broker import (
    SandboxBroker,
)


class OrderCancellationService:
    def __init__(
        self,
        *,
        session: Session,
        broker: SandboxBroker | None = None,
    ) -> None:
        self._order_repository = OrderRepository(
            session
        )

        self._audit_repository = (
            ExecutionAuditRepository(
                session
            )
        )

        self._broker = broker

    def cancel(
        self,
        *,
        order_id: UUID,
    ):
        order = (
            self._order_repository
            .get_by_id(
                order_id
            )
        )

        if order is None:
            raise LookupError(
                f"Order not found: {order_id}"
            )

        terminal_statuses = {
            OrderStatus.FILLED.value,
            OrderStatus.REJECTED.value,
            OrderStatus.CANCELLED.value,
        }

        if order.status in terminal_statuses:
            raise ValueError(
                "Terminal orders cannot be cancelled."
            )

        broker_order_id = (
            order.broker_order_id
        )

        if (
            broker_order_id
            and self._broker is not None
        ):
            self._broker.cancel(
                broker_order_id=(
                    broker_order_id
                )
            )

        cancelled = (
            self._order_repository
            .mark_cancelled(
                order
            )
        )

        self._audit_repository.create(
            account_id=order.account_id,
            order_id=order.id,
            event_type="order_cancelled",
            message=(
                "Paper order was cancelled."
            ),
            event_data={
                "broker_order_id": (
                    broker_order_id
                ),
            },
        )

        return cancelled
