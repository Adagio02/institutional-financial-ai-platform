from uuid import UUID

from sqlalchemy import select
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

        return list(self._session.scalars(statement))
