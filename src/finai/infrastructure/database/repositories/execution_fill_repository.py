from uuid import UUID

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.execution_fill import (
    ExecutionFillModel,
)


class ExecutionFillRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def create(
        self,
        *,
        order_id: UUID,
        quantity: float,
        price: float,
        notional: float,
        commission: float,
        slippage_cost: float,
    ) -> ExecutionFillModel:
        fill = ExecutionFillModel(
            order_id=order_id,
            quantity=quantity,
            price=price,
            notional=notional,
            commission=commission,
            slippage_cost=slippage_cost,
        )

        self._session.add(fill)
        self._session.commit()
        self._session.refresh(fill)

        return fill

    def list_for_order(
        self,
        order_id: UUID,
    ) -> list[ExecutionFillModel]:
        statement = (
            select(ExecutionFillModel)
            .where(ExecutionFillModel.order_id == order_id)
            .order_by(ExecutionFillModel.executed_at)
        )

        return list(self._session.scalars(statement).all())

    def total_filled_quantity(
        self,
        order_id: UUID,
    ) -> float:
        statement = select(
            func.coalesce(
                func.sum(ExecutionFillModel.quantity),
                0.0,
            )
        ).where(ExecutionFillModel.order_id == order_id)

        result = self._session.scalar(statement)

        return float(result or 0.0)

    def weighted_average_price(
        self,
        order_id: UUID,
    ) -> float | None:
        fills = self.list_for_order(order_id)

        if not fills:
            return None

        total_quantity = sum(fill.quantity for fill in fills)

        if total_quantity <= 0:
            return None

        total_notional = sum((fill.quantity * fill.price) for fill in fills)

        return total_notional / total_quantity
