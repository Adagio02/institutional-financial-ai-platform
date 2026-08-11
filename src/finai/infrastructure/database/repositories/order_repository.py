from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.order import (
    OrderModel,
)


class OrderRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def create(
        self,
        *,
        account_id: UUID,
        instrument_id: UUID,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        limit_price: float | None,
        time_in_force: str,
        reference_price: float,
        reference_price_timestamp: datetime,
        reference_price_provider: str,
    ) -> OrderModel:
        order = OrderModel(
            account_id=account_id,
            instrument_id=instrument_id,
            symbol=symbol.strip().upper(),
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
            time_in_force=time_in_force,
            reference_price=reference_price,
            reference_price_timestamp=(
                reference_price_timestamp
            ),
            reference_price_provider=(
                reference_price_provider
            ),
            status="pending",
        )

        self._session.add(
            order
        )

        self._session.commit()

        self._session.refresh(
            order
        )

        return order

    def get_by_id(
        self,
        order_id: UUID,
    ) -> OrderModel | None:
        return self._session.get(
            OrderModel,
            order_id,
        )

    def list_for_account(
        self,
        account_id: UUID,
    ) -> list[OrderModel]:
        statement = (
            select(OrderModel)
            .where(
                OrderModel.account_id
                == account_id
            )
            .order_by(
                OrderModel.created_at.desc()
            )
        )

        return list(
            self._session.scalars(
                statement
            ).all()
        )

    def mark_rejected(
        self,
        order: OrderModel,
        *,
        reason: str,
    ) -> OrderModel:
        order.status = "rejected"

        order.rejection_reason = (
            reason
        )

        self._session.commit()

        self._session.refresh(
            order
        )

        return order

    def mark_filled(
        self,
        order: OrderModel,
        *,
        filled_quantity: float,
        average_fill_price: float,
    ) -> OrderModel:
        order.status = "filled"

        order.filled_quantity = (
            filled_quantity
        )

        order.average_fill_price = (
            average_fill_price
        )

        order.rejection_reason = None

        self._session.commit()

        self._session.refresh(
            order
        )

        return order