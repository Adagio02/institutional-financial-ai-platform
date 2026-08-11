from sqlalchemy.orm import Session

from finai.domain.execution.enums import (
    OrderSide,
    OrderType,
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

        self._broker = PaperBroker(
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
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
            instrument_id=order.instrument_id,
        )

        signed_quantity = fill.quantity if side == OrderSide.BUY else -fill.quantity

        if position is None:
            position = self._position_repository.create(
                account_id=account.id,
                instrument_id=(order.instrument_id),
                symbol=order.symbol,
                quantity=0.0,
                average_price=0.0,
            )

        old_quantity = position.quantity
        new_quantity = old_quantity + signed_quantity

        if (
            old_quantity == 0
            or (old_quantity > 0 and signed_quantity > 0)
            or (old_quantity < 0 and signed_quantity < 0)
        ):
            total_existing_cost = abs(old_quantity) * position.average_price

            total_new_cost = fill.quantity * fill.price

            total_quantity = abs(old_quantity) + fill.quantity

            if total_quantity > 0:
                position.average_price = (total_existing_cost + total_new_cost) / total_quantity

        elif new_quantity == 0:
            position.average_price = 0.0

        position.quantity = new_quantity

        self._position_repository.save(position)

        if side == OrderSide.BUY:
            new_cash = account.cash - fill.notional - fill.commission
        else:
            new_cash = account.cash + fill.notional - fill.commission

        self._account_repository.update_cash(
            account,
            cash=new_cash,
        )

        self._order_repository.mark_filled(
            order,
            filled_quantity=fill.quantity,
            average_fill_price=fill.price,
        )

        return fill
