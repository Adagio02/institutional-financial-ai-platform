from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
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


@dataclass(
    frozen=True,
    slots=True,
)
class AlpacaOrderSnapshot:
    broker_order_id: str

    status: OrderStatus

    requested_quantity: float

    filled_quantity: float

    average_fill_price: float | None

    client_order_id: str | None

    symbol: str

    raw_status: str


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

        resolved_client_order_id = (
            client_order_id
            or f"finai-{order_id}"
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
                    resolved_client_order_id
                ),
            )
        )

        snapshot = (
            self._snapshot_from_response(
                response
            )
        )

        return BrokerExecutionResult(
            broker_order_id=(
                snapshot.broker_order_id
            ),
            status=snapshot.status,
            requested_quantity=(
                snapshot.requested_quantity
            ),
            filled_quantity=(
                snapshot.filled_quantity
            ),
            fills=(),
        )

    def get_snapshot(
        self,
        *,
        broker_order_id: str,
    ) -> AlpacaOrderSnapshot:
        response = self._client.get_order(
            broker_order_id=(
                broker_order_id
            )
        )

        return self._snapshot_from_response(
            response
        )

    def get(
        self,
        *,
        broker_order_id: str,
    ) -> BrokerOrderState:
        snapshot = self.get_snapshot(
            broker_order_id=(
                broker_order_id
            )
        )

        return BrokerOrderState(
            broker_order_id=(
                snapshot.broker_order_id
            ),
            status=snapshot.status,
            requested_quantity=(
                snapshot.requested_quantity
            ),
            filled_quantity=(
                snapshot.filled_quantity
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

        snapshot = self.get_snapshot(
            broker_order_id=(
                broker_order_id
            )
        )

        return BrokerOrderState(
            broker_order_id=(
                snapshot.broker_order_id
            ),
            status=snapshot.status,
            requested_quantity=(
                snapshot.requested_quantity
            ),
            filled_quantity=(
                snapshot.filled_quantity
            ),
            updated_at=datetime.now(UTC),
        )

    @classmethod
    def _snapshot_from_response(
        cls,
        response: dict,
    ) -> AlpacaOrderSnapshot:
        average_fill_raw = response.get(
            "filled_avg_price"
        )

        average_fill_price = None

        if average_fill_raw not in {
            None,
            "",
        }:
            average_fill_price = float(
                average_fill_raw
            )

        raw_status = str(
            response.get(
                "status",
                "accepted",
            )
        )

        return AlpacaOrderSnapshot(
            broker_order_id=str(
                response["id"]
            ),
            status=cls._map_status(
                raw_status
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
            average_fill_price=(
                average_fill_price
            ),
            client_order_id=(
                response.get(
                    "client_order_id"
                )
            ),
            symbol=str(
                response.get(
                    "symbol",
                    "",
                )
            ),
            raw_status=raw_status,
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

        if normalized == "partially_filled":
            return (
                OrderStatus
                .PARTIALLY_FILLED
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