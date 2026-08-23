from sqlalchemy.orm import Session

from finai.application.services.alpaca_fill_accounting_service import (
    AlpacaFillAccountingService,
)
from finai.domain.execution.enums import (
    OrderSide,
    OrderType,
)
from finai.infrastructure.database.repositories.execution_audit_repository import (
    ExecutionAuditRepository,
)
from finai.infrastructure.database.repositories.order_repository import (
    OrderRepository,
)
from finai.infrastructure.execution.alpaca_broker import (
    AlpacaPaperBroker,
)


class AlpacaOrderExecutionService:
    def __init__(
        self,
        *,
        session: Session,
        broker: AlpacaPaperBroker,
        commission_bps: float,
        sync_on_submit: bool,
    ) -> None:
        self._broker = broker

        self._order_repository = (
            OrderRepository(
                session
            )
        )

        self._audit_repository = (
            ExecutionAuditRepository(
                session
            )
        )

        self._accounting_service = (
            AlpacaFillAccountingService(
                session=session,
                commission_bps=(
                    commission_bps
                ),
            )
        )

        self._sync_on_submit = (
            sync_on_submit
        )

    def submit(
        self,
        *,
        order,
        reference_price: float,
    ):
        if order.broker_order_id:
            return order

        result = self._broker.submit(
            order_id=order.id,
            symbol=order.symbol,
            side=OrderSide(
                order.side
            ),
            order_type=OrderType(
                order.order_type
            ),
            quantity=order.quantity,
            reference_price=(
                reference_price
            ),
            limit_price=(
                order.limit_price
            ),
            time_in_force=(
                order.time_in_force
            ),
            client_order_id=(
                order.client_order_id
            ),
        )

        submitted = (
            self._order_repository
            .mark_submitted(
                order,
                broker_order_id=(
                    result.broker_order_id
                ),
                broker_name=(
                    self._broker.name
                ),
            )
        )

        self._audit_repository.create(
            account_id=(
                order.account_id
            ),
            order_id=order.id,
            event_type=(
                "alpaca_order_submitted"
            ),
            message=(
                "Order submitted to "
                "Alpaca paper trading."
            ),
            event_data={
                "broker_order_id": (
                    result.broker_order_id
                ),
                "broker_name": (
                    self._broker.name
                ),
            },
        )

        if self._sync_on_submit:
            return self.sync(
                order=submitted
            )

        return submitted

    def sync(
        self,
        *,
        order,
    ):
        if not order.broker_order_id:
            raise ValueError(
                "Order has no broker "
                "order ID."
            )

        if (
            order.broker_name
            != self._broker.name
        ):
            raise ValueError(
                "Order does not belong "
                "to Alpaca paper."
            )

        snapshot = (
            self._broker.get_snapshot(
                broker_order_id=(
                    order.broker_order_id
                )
            )
        )

        newly_accounted = (
            self._accounting_service
            .apply_cumulative_fill(
                order=order,
                cumulative_filled_quantity=(
                    snapshot
                    .filled_quantity
                ),
                cumulative_average_price=(
                    snapshot
                    .average_fill_price
                ),
            )
        )

        updated = (
            self._order_repository
            .update_fill_state(
                order,
                filled_quantity=(
                    snapshot
                    .filled_quantity
                ),
                average_fill_price=(
                    snapshot
                    .average_fill_price
                ),
                status=snapshot.status,
            )
        )

        self._audit_repository.create(
            account_id=(
                order.account_id
            ),
            order_id=order.id,
            event_type=(
                "alpaca_order_synced"
            ),
            message=(
                "Order synchronized "
                "with Alpaca paper."
            ),
            event_data={
                "broker_order_id": (
                    snapshot
                    .broker_order_id
                ),
                "raw_status": (
                    snapshot.raw_status
                ),
                "filled_quantity": (
                    snapshot
                    .filled_quantity
                ),
                "newly_accounted_quantity": (
                    newly_accounted
                ),
            },
        )

        return updated