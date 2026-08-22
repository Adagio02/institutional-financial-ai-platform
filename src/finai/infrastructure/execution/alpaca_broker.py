from __future__ import annotations

from datetime import (
    UTC,
    datetime,
)
from uuid import UUID

from finai.domain.execution.broker import (
    BrokerExecutionResult,
    BrokerOrderState,
)
from finai.domain.execution.enums import (
    OrderSide,
    OrderStatus,
    OrderType,
)
from finai.infrastructure.execution.alpaca_client import (
    AlpacaPaperClient,
)


class AlpacaPaperBroker:
    def __init__(
        self,
        *,
        client: AlpacaPaperClient,
    ) -> None:
        self._client = client

    @property
    def name(self) -> str:
        return "alpaca-paper"

    def account(
        self,
    ) -> dict:
        return self._client.get_account()

    def submit(
        self,
        *,
        order_id: UUID,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        reference_price: float,
        limit_price: float | None,
        time_in_force: str = "day",
        client_order_id: str | None = None,
    ) -> BrokerExecutionResult:
        del reference_price

        if quantity <= 0:
            raise ValueError(
                "Order quantity must be "
                "positive."
            )

        response = (
            self._client.submit_order(
                symbol=symbol,
                side=side.value,
                order_type=(
                    order_type.value
                ),
                quantity=quantity,
                time_in_force=(
                    time_in_force
                ),
                limit_price=limit_price,
                client_order_id=(
                    client_order_id
                    or f"finai-{order_id}"
                ),
            )
        )

        broker_order_id = str(
            response["id"]
        )

        requested_quantity = float(
            response.get(
                "qty",
                quantity,
            )
        )

        filled_quantity = float(
            response.get(
                "filled_qty",
                0.0,
            )
        )

        status = self._map_status(
            str(
                response.get(
                    "status",
                    "accepted",
                )
            )
        )

        return BrokerExecutionResult(
            broker_order_id=(
                broker_order_id
            ),
            status=status,
            requested_quantity=(
                requested_quantity
            ),
            filled_quantity=(
                filled_quantity
            ),
            fills=(),
        )

    def get(
        self,
        *,
        broker_order_id: str,
    ) -> BrokerOrderState:
        response = self._client.get_order(
            broker_order_id=(
                broker_order_id
            )
        )

        return BrokerOrderState(
            broker_order_id=str(
                response["id"]
            ),
            status=self._map_status(
                str(
                    response.get(
                        "status",
                        "accepted",
                    )
                )
            ),
            requested_quantity=float(
                response.get(
                    "qty",
                    0.0,
                )
            ),
            filled_quantity=float(
                response.get(
                    "filled_qty",
                    0.0,
                )
            ),
            updated_at=datetime.now(UTC),
        )

    def cancel(
        self,
        *,
        broker_order_id: str,
    ) -> BrokerOrderState:
        self._client.cancel_order(
            broker_order_id=(
                broker_order_id
            )
        )

        return BrokerOrderState(
            broker_order_id=(
                broker_order_id
            ),
            status=(
                OrderStatus.CANCELLED
            ),
            requested_quantity=0.0,
            filled_quantity=0.0,
            updated_at=datetime.now(UTC),
        )

    @staticmethod
    def _map_status(
        alpaca_status: str,
    ) -> OrderStatus:
        normalized = (
            alpaca_status
            .strip()
            .lower()
        )

        if normalized == "filled":
            return OrderStatus.FILLED

        if normalized in {
            "partially_filled",
        }:
            return (
                OrderStatus.PARTIALLY_FILLED
            )

        if normalized in {
            "canceled",
            "cancelled",
            "expired",
        }:
            return OrderStatus.CANCELLED

        if normalized in {
            "rejected",
        }:
            return OrderStatus.REJECTED

        return OrderStatus.ACCEPTED