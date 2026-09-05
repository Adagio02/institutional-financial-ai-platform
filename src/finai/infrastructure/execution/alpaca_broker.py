from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    UTC,
    datetime,
)
from uuid import UUID

from finai.domain.execution.alpaca_account_guard import (
    AlpacaAccountGuard,
    AlpacaAccountGuardResult,
)
from finai.domain.execution.alpaca_idempotency_guard import (
    AlpacaIdempotencyGuard,
)
from finai.domain.execution.alpaca_market_guard import (
    AlpacaMarketGuard,
    AlpacaMarketGuardResult,
)
from finai.domain.execution.alpaca_quote_guard import (
    AlpacaQuoteGuard,
    AlpacaQuoteGuardResult,
)
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
    AlpacaOrderNotFoundError,
    AlpacaPaperClient,
    AlpacaTransportError,
)
from finai.infrastructure.market_data.alpaca_market_data_client import (
    AlpacaMarketDataClient,
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

    average_fill_price: (
        float | None
    )

    client_order_id: (
        str | None
    )

    symbol: str

    raw_status: str

    side: str | None = None

    order_type: str | None = None

    time_in_force: str | None = None


class AlpacaPaperBroker:
    def __init__(
        self,
        *,
        client: AlpacaPaperClient,
        account_guard: (
            AlpacaAccountGuard
            | None
        ) = None,
        market_guard: (
            AlpacaMarketGuard
            | None
        ) = None,
        idempotency_guard: (
            AlpacaIdempotencyGuard
            | None
        ) = None,
        market_data_client: (
            AlpacaMarketDataClient
            | None
        ) = None,
        quote_guard: (
            AlpacaQuoteGuard
            | None
        ) = None,
        lookup_before_submit: bool = True,
        recover_after_transport_error: bool = True,
    ) -> None:
        self._client = client

        self._account_guard = (
            account_guard
        )

        self._market_guard = (
            market_guard
        )

        self._idempotency_guard = (
            idempotency_guard
        )

        self._market_data_client = (
            market_data_client
        )

        self._quote_guard = (
            quote_guard
        )

        self._lookup_before_submit = (
            lookup_before_submit
        )

        self._recover_after_transport_error = (
            recover_after_transport_error
        )

        if (
            self._quote_guard is not None
            and (
                self._market_data_client
                is None
            )
        ):
            raise ValueError(
                "Alpaca quote guard "
                "requires an Alpaca "
                "market-data client."
            )

    @property
    def name(
        self,
    ) -> str:
        return "alpaca-paper"

    def account(
        self,
    ) -> dict:
        return (
            self._client
            .get_account()
        )

    def validate_account_submission(
        self,
        *,
        side: OrderSide,
        quantity: float,
        reference_price: float,
    ) -> (
        AlpacaAccountGuardResult
        | None
    ):
        if (
            self._account_guard
            is None
        ):
            return None

        return (
            self._account_guard
            .validate_order(
                account=self.account(),
                side=side,
                quantity=quantity,
                reference_price=(
                    reference_price
                ),
            )
        )

    def validate_market_submission(
        self,
        *,
        symbol: str,
        quantity: float,
    ) -> (
        AlpacaMarketGuardResult
        | None
    ):
        if (
            self._market_guard
            is None
        ):
            return None

        asset = (
            self._client
            .get_asset(
                symbol=symbol
            )
        )

        clock = (
            self._client
            .get_clock()
        )

        return (
            self._market_guard
            .validate_order(
                asset=asset,
                clock=clock,
                symbol=symbol,
                quantity=quantity,
            )
        )

    def validate_quote_submission(
        self,
        *,
        symbol: str,
        reference_price: float,
    ) -> (
        AlpacaQuoteGuardResult
        | None
    ):
        if self._quote_guard is None:
            return None

        if (
            self._market_data_client
            is None
        ):
            raise RuntimeError(
                "Alpaca market-data client "
                "is not configured."
            )

        quote = (
            self._market_data_client
            .get_latest_quote(
                symbol=symbol
            )
        )

        return (
            self._quote_guard
            .validate_quote(
                symbol=symbol,
                quote=quote,
                reference_price=(
                    reference_price
                ),
            )
        )

    def validate_submission(
        self,
        *,
        symbol: str,
        side: OrderSide,
        quantity: float,
        reference_price: float,
    ) -> tuple[
        (
            AlpacaAccountGuardResult
            | None
        ),
        (
            AlpacaMarketGuardResult
            | None
        ),
        (
            AlpacaQuoteGuardResult
            | None
        ),
    ]:
        market_result = (
            self.validate_market_submission(
                symbol=symbol,
                quantity=quantity,
            )
        )

        quote_result = (
            self.validate_quote_submission(
                symbol=symbol,
                reference_price=(
                    reference_price
                ),
            )
        )

        account_result = (
            self.validate_account_submission(
                side=side,
                quantity=quantity,
                reference_price=(
                    reference_price
                ),
            )
        )

        return (
            account_result,
            market_result,
            quote_result,
        )

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
        client_order_id: (
            str | None
        ) = None,
    ) -> BrokerExecutionResult:
        if quantity <= 0:
            raise ValueError(
                "Order quantity must "
                "be positive."
            )

        resolved_client_order_id = (
            client_order_id
            or f"finai-{order_id}"
        )

        if (
            self._idempotency_guard
            is not None
        ):
            resolved_client_order_id = (
                self._idempotency_guard
                .validate_client_order_id(
                    resolved_client_order_id
                )
            )

        if (
            self._idempotency_guard
            is not None
            and self._lookup_before_submit
        ):
            existing = (
                self._find_existing_order(
                    client_order_id=(
                        resolved_client_order_id
                    )
                )
            )

            if existing is not None:
                return (
                    self._recover_existing(
                        existing_order=(
                            existing
                        ),
                        client_order_id=(
                            resolved_client_order_id
                        ),
                        symbol=symbol,
                        side=side,
                        order_type=(
                            order_type
                        ),
                        quantity=quantity,
                        time_in_force=(
                            time_in_force
                        ),
                    )
                )

        self.validate_submission(
            symbol=symbol,
            side=side,
            quantity=quantity,
            reference_price=(
                reference_price
            ),
        )

        try:
            response = (
                self._client
                .submit_order(
                    symbol=symbol,
                    side=side.value,
                    order_type=(
                        order_type.value
                    ),
                    quantity=quantity,
                    time_in_force=(
                        time_in_force
                    ),
                    limit_price=(
                        limit_price
                    ),
                    client_order_id=(
                        resolved_client_order_id
                    ),
                )
            )

        except AlpacaTransportError:
            if not (
                self._idempotency_guard
                is not None
                and (
                    self
                    ._recover_after_transport_error
                )
            ):
                raise

            existing = (
                self._find_existing_order(
                    client_order_id=(
                        resolved_client_order_id
                    )
                )
            )

            if existing is None:
                raise

            return (
                self._recover_existing(
                    existing_order=(
                        existing
                    ),
                    client_order_id=(
                        resolved_client_order_id
                    ),
                    symbol=symbol,
                    side=side,
                    order_type=(
                        order_type
                    ),
                    quantity=quantity,
                    time_in_force=(
                        time_in_force
                    ),
                )
            )

        return (
            self._execution_result_from_response(
                response
            )
        )

    def _find_existing_order(
        self,
        *,
        client_order_id: str,
    ) -> dict | None:
        try:
            return (
                self._client
                .get_order_by_client_order_id(
                    client_order_id=(
                        client_order_id
                    )
                )
            )

        except AlpacaOrderNotFoundError:
            return None

    def _recover_existing(
        self,
        *,
        existing_order: dict,
        client_order_id: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        time_in_force: str,
    ) -> BrokerExecutionResult:
        if (
            self._idempotency_guard
            is None
        ):
            raise RuntimeError(
                "Alpaca idempotency guard "
                "is not configured."
            )

        (
            self._idempotency_guard
            .validate_existing_order(
                existing_order=(
                    existing_order
                ),
                client_order_id=(
                    client_order_id
                ),
                symbol=symbol,
                side=side.value,
                order_type=(
                    order_type.value
                ),
                quantity=quantity,
                time_in_force=(
                    time_in_force
                ),
            )
        )

        return (
            self._execution_result_from_response(
                existing_order
            )
        )

    def _execution_result_from_response(
        self,
        response: dict,
    ) -> BrokerExecutionResult:
        snapshot = (
            self.snapshot_from_response(
                response
            )
        )

        return BrokerExecutionResult(
            broker_order_id=(
                snapshot.broker_order_id
            ),
            status=(
                snapshot.status
            ),
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
        response = (
            self._client
            .get_order(
                broker_order_id=(
                    broker_order_id
                )
            )
        )

        return (
            self.snapshot_from_response(
                response
            )
        )

    def get_snapshot_by_client_order_id(
        self,
        *,
        client_order_id: str,
    ) -> AlpacaOrderSnapshot:
        response = (
            self._client
            .get_order_by_client_order_id(
                client_order_id=(
                    client_order_id
                )
            )
        )

        return (
            self.snapshot_from_response(
                response
            )
        )

    def list_snapshots(
        self,
        *,
        status: str,
        limit: int,
        direction: str,
    ) -> list[
        AlpacaOrderSnapshot
    ]:
        responses = (
            self._client
            .list_orders(
                status=status,
                limit=limit,
                direction=direction,
                nested=False,
            )
        )

        return [
            self.snapshot_from_response(
                response
            )
            for response
            in responses
        ]

    def get(
        self,
        *,
        broker_order_id: str,
    ) -> BrokerOrderState:
        snapshot = (
            self.get_snapshot(
                broker_order_id=(
                    broker_order_id
                )
            )
        )

        return BrokerOrderState(
            broker_order_id=(
                snapshot.broker_order_id
            ),
            status=(
                snapshot.status
            ),
            requested_quantity=(
                snapshot.requested_quantity
            ),
            filled_quantity=(
                snapshot.filled_quantity
            ),
            updated_at=(
                datetime.now(UTC)
            ),
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

        snapshot = (
            self.get_snapshot(
                broker_order_id=(
                    broker_order_id
                )
            )
        )

        return BrokerOrderState(
            broker_order_id=(
                snapshot.broker_order_id
            ),
            status=(
                snapshot.status
            ),
            requested_quantity=(
                snapshot.requested_quantity
            ),
            filled_quantity=(
                snapshot.filled_quantity
            ),
            updated_at=(
                datetime.now(UTC)
            ),
        )

    @classmethod
    def snapshot_from_response(
        cls,
        response: dict,
    ) -> AlpacaOrderSnapshot:
        broker_order_id = str(
            response.get(
                "id",
                "",
            )
        ).strip()

        if not broker_order_id:
            raise ValueError(
                "Alpaca order response "
                "contains no order ID."
            )

        average_fill_raw = (
            response.get(
                "filled_avg_price"
            )
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

        side_raw = response.get(
            "side"
        )

        type_raw = response.get(
            "type"
        )

        time_in_force_raw = (
            response.get(
                "time_in_force"
            )
        )

        return AlpacaOrderSnapshot(
            broker_order_id=(
                broker_order_id
            ),
            status=(
                cls._map_status(
                    raw_status
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
            )
            .strip()
            .upper(),
            raw_status=(
                raw_status
            ),
            side=(
                None
                if side_raw is None
                else str(
                    side_raw
                )
                .strip()
                .lower()
            ),
            order_type=(
                None
                if type_raw is None
                else str(
                    type_raw
                )
                .strip()
                .lower()
            ),
            time_in_force=(
                None
                if time_in_force_raw
                is None
                else str(
                    time_in_force_raw
                )
                .strip()
                .lower()
            ),
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

        if (
            normalized
            == "partially_filled"
        ):
            return (
                OrderStatus
                .PARTIALLY_FILLED
            )

        if normalized in {
            "canceled",
            "cancelled",
            "expired",
        }:
            return (
                OrderStatus.CANCELLED
            )

        if normalized == "rejected":
            return OrderStatus.REJECTED

        return OrderStatus.ACCEPTED