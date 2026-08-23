from datetime import (
    UTC,
    datetime,
)
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.domain.execution.enums import (
    OrderStatus,
)
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
        client_order_id: str | None,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        limit_price: float | None,
        time_in_force: str,
        reference_price: float,
        reference_price_timestamp: datetime,
        reference_price_provider: str,
        strategy_key: str | None,
    ) -> OrderModel:
        order = OrderModel(
            account_id=account_id,
            instrument_id=(
                instrument_id
            ),
            client_order_id=(
                client_order_id
            ),
            symbol=(
                symbol
                .strip()
                .upper()
            ),
            side=side,
            order_type=order_type,
            quantity=quantity,
            filled_quantity=0.0,
            remaining_quantity=(
                quantity
            ),
            limit_price=limit_price,
            time_in_force=(
                time_in_force
            ),
            reference_price=(
                reference_price
            ),
            reference_price_timestamp=(
                reference_price_timestamp
            ),
            reference_price_provider=(
                reference_price_provider
            ),
            status=(
                OrderStatus
                .PENDING
                .value
            ),
            strategy_key=(
                strategy_key
            ),
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

    def get_by_broker_order_id(
        self,
        broker_order_id: str,
    ) -> OrderModel | None:
        normalized = (
            broker_order_id.strip()
        )

        if not normalized:
            return None

        statement = (
            select(OrderModel)
            .where(
                OrderModel
                .broker_order_id
                == normalized
            )
        )

        return self._session.scalar(
            statement
        )

    def get_by_client_order_id(
        self,
        *,
        account_id: UUID,
        client_order_id: str,
    ) -> OrderModel | None:
        statement = (
            select(OrderModel)
            .where(
                OrderModel.account_id
                == account_id,
                OrderModel.client_order_id
                == client_order_id,
            )
        )

        return self._session.scalar(
            statement
        )

    def list_by_client_order_id(
        self,
        client_order_id: str,
    ) -> list[OrderModel]:
        normalized = (
            client_order_id.strip()
        )

        if not normalized:
            return []

        statement = (
            select(OrderModel)
            .where(
                OrderModel
                .client_order_id
                == normalized
            )
            .order_by(
                OrderModel.created_at
            )
        )

        return list(
            self._session
            .scalars(
                statement
            )
            .all()
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
                OrderModel
                .created_at
                .desc()
            )
        )

        return list(
            self._session
            .scalars(
                statement
            )
            .all()
        )

    def list_for_broker(
        self,
        *,
        broker_name: str,
        limit: int,
    ) -> list[OrderModel]:
        normalized = (
            broker_name.strip()
        )

        if not normalized:
            raise ValueError(
                "broker_name cannot "
                "be blank."
            )

        if limit <= 0:
            raise ValueError(
                "limit must be positive."
            )

        statement = (
            select(OrderModel)
            .where(
                OrderModel.broker_name
                == normalized
            )
            .order_by(
                OrderModel
                .created_at
                .desc()
            )
            .limit(limit)
        )

        return list(
            self._session
            .scalars(
                statement
            )
            .all()
        )

    def list_open(
        self,
    ) -> list[OrderModel]:
        statement = (
            select(OrderModel)
            .where(
                OrderModel.status.in_(
                    [
                        OrderStatus
                        .PENDING
                        .value,
                        OrderStatus
                        .ACCEPTED
                        .value,
                        OrderStatus
                        .PARTIALLY_FILLED
                        .value,
                    ]
                )
            )
            .order_by(
                OrderModel.created_at
            )
        )

        return list(
            self._session
            .scalars(
                statement
            )
            .all()
        )

    def list_open_for_broker(
        self,
        *,
        broker_name: str,
        limit: int,
    ) -> list[OrderModel]:
        normalized = (
            broker_name.strip()
        )

        if not normalized:
            raise ValueError(
                "broker_name cannot "
                "be blank."
            )

        if limit <= 0:
            raise ValueError(
                "limit must be positive."
            )

        statement = (
            select(OrderModel)
            .where(
                OrderModel.broker_name
                == normalized,
                OrderModel.status.in_(
                    [
                        OrderStatus
                        .PENDING
                        .value,
                        OrderStatus
                        .ACCEPTED
                        .value,
                        OrderStatus
                        .PARTIALLY_FILLED
                        .value,
                    ]
                ),
            )
            .order_by(
                OrderModel.created_at
            )
            .limit(limit)
        )

        return list(
            self._session
            .scalars(
                statement
            )
            .all()
        )

    def attach_broker_identity(
        self,
        order: OrderModel,
        *,
        broker_order_id: str,
        broker_name: str,
    ) -> OrderModel:
        normalized_order_id = (
            broker_order_id.strip()
        )

        normalized_broker_name = (
            broker_name.strip()
        )

        if not normalized_order_id:
            raise ValueError(
                "broker_order_id cannot "
                "be blank."
            )

        if not normalized_broker_name:
            raise ValueError(
                "broker_name cannot "
                "be blank."
            )

        if (
            order.broker_order_id
            is not None
            and order.broker_order_id
            != normalized_order_id
        ):
            raise ValueError(
                "Order already belongs "
                "to another broker order."
            )

        if (
            order.broker_name
            is not None
            and order.broker_name
            != normalized_broker_name
        ):
            raise ValueError(
                "Order already belongs "
                "to another broker."
            )

        order.broker_order_id = (
            normalized_order_id
        )

        order.broker_name = (
            normalized_broker_name
        )

        if order.submitted_at is None:
            order.submitted_at = (
                datetime.now(UTC)
            )

        if (
            order.status
            == OrderStatus.PENDING.value
        ):
            order.status = (
                OrderStatus
                .ACCEPTED
                .value
            )

        order.last_synced_at = (
            datetime.now(UTC)
        )

        self._session.commit()

        self._session.refresh(
            order
        )

        return order

    def mark_submitted(
        self,
        order: OrderModel,
        *,
        broker_order_id: str,
        broker_name: str,
    ) -> OrderModel:
        order.broker_order_id = (
            broker_order_id
        )

        order.broker_name = (
            broker_name
        )

        order.status = (
            OrderStatus
            .ACCEPTED
            .value
        )

        order.submitted_at = (
            datetime.now(UTC)
        )

        order.last_synced_at = (
            datetime.now(UTC)
        )

        self._session.commit()

        self._session.refresh(
            order
        )

        return order

    def update_fill_state(
        self,
        order: OrderModel,
        *,
        filled_quantity: float,
        average_fill_price: (
            float | None
        ),
        status: OrderStatus,
    ) -> OrderModel:
        order.filled_quantity = (
            filled_quantity
        )

        order.remaining_quantity = max(
            order.quantity
            - filled_quantity,
            0.0,
        )

        order.average_fill_price = (
            average_fill_price
        )

        order.status = (
            status.value
        )

        order.last_synced_at = (
            datetime.now(UTC)
        )

        self._session.commit()

        self._session.refresh(
            order
        )

        return order

    def touch_synced(
        self,
        order: OrderModel,
    ) -> OrderModel:
        order.last_synced_at = (
            datetime.now(UTC)
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
        order.filled_quantity = (
            filled_quantity
        )

        order.remaining_quantity = max(
            order.quantity
            - filled_quantity,
            0.0,
        )

        order.average_fill_price = (
            average_fill_price
        )

        order.status = (
            OrderStatus
            .FILLED
            .value
        )

        order.last_synced_at = (
            datetime.now(UTC)
        )

        self._session.commit()

        self._session.refresh(
            order
        )

        return order

    def mark_rejected(
        self,
        order: OrderModel,
        *,
        reason: str,
    ) -> OrderModel:
        order.status = (
            OrderStatus
            .REJECTED
            .value
        )

        order.rejection_reason = (
            reason
        )

        order.remaining_quantity = (
            order.quantity
            - order.filled_quantity
        )

        order.last_synced_at = (
            datetime.now(UTC)
        )

        self._session.commit()

        self._session.refresh(
            order
        )

        return order

    def mark_cancelled(
        self,
        order: OrderModel,
    ) -> OrderModel:
        order.status = (
            OrderStatus
            .CANCELLED
            .value
        )

        order.cancelled_at = (
            datetime.now(UTC)
        )

        order.last_synced_at = (
            datetime.now(UTC)
        )

        self._session.commit()

        self._session.refresh(
            order
        )

        return order