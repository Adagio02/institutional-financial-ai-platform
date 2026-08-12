from sqlalchemy.orm import Session

from finai.domain.execution.enums import (
    OrderSide,
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
from finai.infrastructure.execution.paper_broker import (
    PaperBroker,
)


class PaperExecutionService:
    def __init__(
        self,
        *,
        session: Session,
        commission_bps: float,
        slippage_bps: float,
    ) -> None:
        self._account_repository = PaperAccountRepository(session)

        self._order_repository = OrderRepository(session)

        self._fill_repository = ExecutionFillRepository(session)

        self._position_repository = PaperPositionRepository(session)

        self._audit_repository = ExecutionAuditRepository(session)

        self._broker = PaperBroker(
            commission_bps=(commission_bps),
            slippage_bps=(slippage_bps),
        )

    def execute(
        self,
        *,
        order,
        reference_price: float,
    ):
        account = self._account_repository.get_by_id(order.account_id)

        if account is None:
            raise LookupError("Paper account was not found.")

        side = OrderSide(order.side)

        order_type = OrderType(order.order_type)

        fill = self._broker.execute(
            side=side,
            order_type=order_type,
            quantity=order.quantity,
            reference_price=reference_price,
            limit_price=order.limit_price,
        )

        if fill is None:
            self._audit_repository.create(
                account_id=account.id,
                order_id=order.id,
                event_type=("order_not_filled"),
                message=("Paper order did not satisfy execution rules."),
            )

            return None

        self._fill_repository.create(
            order_id=order.id,
            quantity=fill.quantity,
            price=fill.price,
            notional=fill.notional,
            commission=fill.commission,
            slippage_cost=(fill.slippage_cost),
        )

        position = self._position_repository.get(
            account_id=account.id,
            instrument_id=(order.instrument_id),
        )

        if position is None:
            position = self._position_repository.create(
                account_id=(account.id),
                instrument_id=(order.instrument_id),
                symbol=order.symbol,
                quantity=0.0,
                average_price=0.0,
            )

        signed_fill_quantity = fill.quantity if side == OrderSide.BUY else -fill.quantity

        accounting_result = apply_fill_to_position(
            current_quantity=(position.quantity),
            current_average_price=(position.average_price),
            fill_quantity=(signed_fill_quantity),
            fill_price=fill.price,
        )

        position.quantity = accounting_result.quantity

        position.average_price = accounting_result.average_price

        position.realized_pnl += accounting_result.realized_pnl_delta

        self._position_repository.save(position)

        if side == OrderSide.BUY:
            new_cash = account.cash - fill.notional - fill.commission

        else:
            new_cash = account.cash + fill.notional - fill.commission

        new_realized_pnl = (
            account.realized_pnl + accounting_result.realized_pnl_delta - fill.commission
        )

        self._account_repository.update_cash(
            account,
            cash=new_cash,
            realized_pnl=(new_realized_pnl),
        )

        self._order_repository.mark_filled(
            order,
            filled_quantity=(fill.quantity),
            average_fill_price=(fill.price),
        )

        self._audit_repository.create(
            account_id=account.id,
            order_id=order.id,
            event_type="order_filled",
            message=("Paper order was filled."),
            event_data={
                "symbol": order.symbol,
                "side": order.side,
                "quantity": fill.quantity,
                "price": fill.price,
                "commission": (fill.commission),
                "realized_pnl_delta": (accounting_result.realized_pnl_delta),
            },
        )

        return fill
