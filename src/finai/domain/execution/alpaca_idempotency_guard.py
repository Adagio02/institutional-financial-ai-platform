from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class AlpacaIdempotencyMatch:
    broker_order_id: str
    client_order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    time_in_force: str
    status: str


class AlpacaIdempotencyGuard:
    def __init__(
        self,
        *,
        require_order_match: bool,
    ) -> None:
        self._require_order_match = (
            require_order_match
        )

    def validate_existing_order(
        self,
        *,
        existing_order: dict[str, Any],
        client_order_id: str,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        time_in_force: str,
    ) -> AlpacaIdempotencyMatch:
        normalized_client_order_id = (
            client_order_id.strip()
        )

        if not normalized_client_order_id:
            raise ValueError(
                "client_order_id cannot "
                "be blank."
            )

        if len(
            normalized_client_order_id
        ) > 128:
            raise ValueError(
                "client_order_id cannot "
                "exceed 128 characters."
            )

        broker_order_id = str(
            existing_order.get(
                "id",
                "",
            )
        ).strip()

        if not broker_order_id:
            raise ValueError(
                "Existing Alpaca order "
                "contains no broker ID."
            )

        existing_client_order_id = str(
            existing_order.get(
                "client_order_id",
                "",
            )
        ).strip()

        existing_symbol = str(
            existing_order.get(
                "symbol",
                "",
            )
        ).strip().upper()

        existing_side = str(
            existing_order.get(
                "side",
                "",
            )
        ).strip().lower()

        existing_order_type = str(
            existing_order.get(
                "type",
                existing_order.get(
                    "order_type",
                    "",
                ),
            )
        ).strip().lower()

        existing_time_in_force = str(
            existing_order.get(
                "time_in_force",
                "",
            )
        ).strip().lower()

        existing_quantity = self._as_float(
            existing_order.get(
                "qty"
            ),
            field_name="qty",
        )

        existing_status = str(
            existing_order.get(
                "status",
                "",
            )
        ).strip().lower()

        if (
            existing_client_order_id
            != normalized_client_order_id
        ):
            raise ValueError(
                "Alpaca returned an order "
                "with a different "
                "client_order_id."
            )

        if self._require_order_match:
            expected_symbol = (
                symbol
                .strip()
                .upper()
            )

            expected_side = (
                side
                .strip()
                .lower()
            )

            expected_order_type = (
                order_type
                .strip()
                .lower()
            )

            expected_time_in_force = (
                time_in_force
                .strip()
                .lower()
            )

            if (
                existing_symbol
                != expected_symbol
            ):
                raise ValueError(
                    "Existing Alpaca order "
                    "symbol does not match "
                    "the requested order."
                )

            if (
                existing_side
                != expected_side
            ):
                raise ValueError(
                    "Existing Alpaca order "
                    "side does not match "
                    "the requested order."
                )

            if (
                existing_order_type
                != expected_order_type
            ):
                raise ValueError(
                    "Existing Alpaca order "
                    "type does not match "
                    "the requested order."
                )

            if (
                abs(
                    existing_quantity
                    - float(quantity)
                )
                > 1e-9
            ):
                raise ValueError(
                    "Existing Alpaca order "
                    "quantity does not match "
                    "the requested order."
                )

            if (
                existing_time_in_force
                != expected_time_in_force
            ):
                raise ValueError(
                    "Existing Alpaca order "
                    "time_in_force does not "
                    "match the requested order."
                )

        return AlpacaIdempotencyMatch(
            broker_order_id=(
                broker_order_id
            ),
            client_order_id=(
                existing_client_order_id
            ),
            symbol=existing_symbol,
            side=existing_side,
            order_type=(
                existing_order_type
            ),
            quantity=(
                existing_quantity
            ),
            time_in_force=(
                existing_time_in_force
            ),
            status=(
                existing_status
            ),
        )

    @staticmethod
    def validate_client_order_id(
        client_order_id: str,
    ) -> str:
        normalized = (
            client_order_id.strip()
        )

        if not normalized:
            raise ValueError(
                "client_order_id cannot "
                "be blank."
            )

        if len(normalized) > 128:
            raise ValueError(
                "client_order_id cannot "
                "exceed 128 characters."
            )

        return normalized

    @staticmethod
    def _as_float(
        value: Any,
        *,
        field_name: str,
    ) -> float:
        if value in {
            None,
            "",
        }:
            raise ValueError(
                f"Alpaca order field "
                f"{field_name} is missing."
            )

        try:
            return float(
                value
            )

        except (
            TypeError,
            ValueError,
        ) as error:
            raise ValueError(
                f"Alpaca order field "
                f"{field_name} is invalid."
            ) from error