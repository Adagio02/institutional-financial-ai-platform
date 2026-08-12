from sqlalchemy.orm import Session

from finai.domain.execution.broker import (
    BrokerAdapter,
    BrokerExecutionResult,
)
from finai.domain.execution.enums import (
    OrderSide,
    OrderStatus,
    OrderType,
)
from finai.domain.execution.position_accounting import (
    apply_fill_to_position,
)
from finai.infrastructure.database.repositories.execution_audit_repository import (
    ExecutionAuditRepository,
)
from finai.infrastructure.database.repositories.execution_fill_repository import (
    ExecutionFillRepository,
)
from finai.infrastructure.database.repositories.order_repository import (
    OrderRepository,
)
from finai.infrastructure.database.repositories.paper_account_repository import (
    PaperAccountRepository,
)
from finai.infrastructure.database.repositories.paper_position_repository import (
    PaperPositionRepository,
)


class BrokerExecutionService:
    def __init__(
        self,
        *,
        session: Session,
        broker: BrokerAdapter,
    ) -> None:
        self._broker = broker

        self._account_repository = PaperAccountRepository(session)

        self._order_repository = OrderRepository(session)

        self._fill_repository = ExecutionFillRepository(session)

        self._position_repository = PaperPositionRepository(session)

        self._audit_repository = ExecutionAuditRepository(session)

    def execute(
        self,
        *,
        order,
        reference_price: float,
    ):
        account = self._account_repository.get_by_id(order.account_id)

        if account is None:
            raise LookupError("Paper account was not found.")

        result = self._broker.submit(
            order_id=order.id,
            symbol=order.symbol,
            side=OrderSide(order.side),
            order_type=OrderType(order.order_type),
            quantity=(order.remaining_quantity),
            reference_price=(reference_price),
            limit_price=(order.limit_price),
        )

        self._order_repository.mark_submitted(
            order,
            broker_order_id=(result.broker_order_id),
            broker_name=(self._broker.name),
        )

        self._apply_result(
            order=order,
            result=result,
        )

        return self._order_repository.get_by_id(order.id)

    def _apply_result(
        self,
        *,
        order,
        result: BrokerExecutionResult,
    ) -> None:
        if not result.fills:
            self._order_repository.update_fill_state(
                order,
                filled_quantity=(order.filled_quantity),
                average_fill_price=(order.average_fill_price),
                status=result.status,
            )

            return

        account = self._account_repository.get_by_id(order.account_id)

        if account is None:
            raise LookupError("Paper account was not found.")

        side = OrderSide(order.side)

        position = self._position_repository.get(
            account_id=account.id,
            instrument_id=(order.instrument_id),
        )

        if position is None:
            position = self._position_repository.create(
                account_id=account.id,
                instrument_id=(order.instrument_id),
                symbol=order.symbol,
                quantity=0.0,
                average_price=0.0,
            )

        for fill in result.fills:
            notional = fill.quantity * fill.price

            self._fill_repository.create(
                order_id=order.id,
                quantity=fill.quantity,
                price=fill.price,
                notional=notional,
                commission=(fill.commission),
                slippage_cost=(fill.slippage_cost),
            )

            signed_quantity = fill.quantity if side == OrderSide.BUY else -fill.quantity

            accounting = apply_fill_to_position(
                current_quantity=(position.quantity),
                current_average_price=(position.average_price),
                fill_quantity=(signed_quantity),
                fill_price=(fill.price),
            )

            position.quantity = accounting.quantity

            position.average_price = accounting.average_price

            position.realized_pnl += accounting.realized_pnl_delta

            self._position_repository.save(position)

            if side == OrderSide.BUY:
                account.cash -= notional + fill.commission
            else:
                account.cash += notional - fill.commission

            account.realized_pnl += accounting.realized_pnl_delta - fill.commission

            self._account_repository.update_cash(
                account,
                cash=account.cash,
                realized_pnl=(account.realized_pnl),
            )

        total_filled = self._fill_repository.total_filled_quantity(order.id)

        average_price = self._fill_repository.weighted_average_price(order.id)

        if total_filled >= order.quantity:
            status = OrderStatus.FILLED
        else:
            status = OrderStatus.PARTIALLY_FILLED

        self._order_repository.update_fill_state(
            order,
            filled_quantity=(total_filled),
            average_fill_price=(average_price),
            status=status,
        )

        self._audit_repository.create(
            account_id=account.id,
            order_id=order.id,
            event_type=("broker_execution_update"),
            message=("Sandbox broker execution was applied."),
            event_data={
                "broker": (self._broker.name),
                "status": status.value,
                "filled_quantity": (total_filled),
                "remaining_quantity": (
                    max(
                        order.quantity - total_filled,
                        0.0,
                    )
                ),
            },
        )
