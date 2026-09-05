from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from finai.application.services.alpaca_order_execution_service import (
    AlpacaOrderExecutionService,
)
from finai.application.services.alpaca_orphan_recovery_service import (
    AlpacaOrphanRecoveryService,
)
from finai.infrastructure.database.repositories.order_repository import (
    OrderRepository,
)
from finai.infrastructure.execution.alpaca_broker import (
    AlpacaOrderSnapshot,
    AlpacaPaperBroker,
)


@dataclass(
    frozen=True,
    slots=True,
)
class BrokerOnlyOrder:
    broker_order_id: str

    client_order_id: (
        str | None
    )

    symbol: str

    status: str

    reason: str


@dataclass(
    frozen=True,
    slots=True,
)
class AlpacaOrderDiscoveryResult:
    remote_orders: int

    remote_open_orders: int

    local_orders: int

    matched: int

    synchronized: int

    refreshed: int

    recovered: int

    broker_only: tuple[
        BrokerOnlyOrder,
        ...,
    ]

    local_open_missing_remote: (
        tuple[UUID, ...]
    )

    remote_open_truncated: bool


class AlpacaOrderDiscoveryService:
    def __init__(
        self,
        *,
        session: Session,
        broker: AlpacaPaperBroker,
        execution_service: (
            AlpacaOrderExecutionService
        ),
        limit: int,
        direction: str,
        orphan_recovery_service: (
            AlpacaOrphanRecoveryService
            | None
        ) = None,
    ) -> None:
        if not (
            1
            <= limit
            <= 500
        ):
            raise ValueError(
                "limit must be between "
                "1 and 500."
            )

        normalized_direction = (
            direction
            .strip()
            .lower()
        )

        if normalized_direction not in {
            "asc",
            "desc",
        }:
            raise ValueError(
                "direction must be "
                "'asc' or 'desc'."
            )

        self._repository = (
            OrderRepository(
                session
            )
        )

        self._broker = broker

        self._execution_service = (
            execution_service
        )

        self._limit = limit

        self._direction = (
            normalized_direction
        )

        self._orphan_recovery_service = (
            orphan_recovery_service
        )

    def discover(
        self,
    ) -> AlpacaOrderDiscoveryResult:
        remote_orders = (
            self._broker
            .list_snapshots(
                status="all",
                limit=self._limit,
                direction=(
                    self._direction
                ),
            )
        )

        remote_open_orders = (
            self._broker
            .list_snapshots(
                status="open",
                limit=self._limit,
                direction=(
                    self._direction
                ),
            )
        )

        local_orders = (
            self._repository
            .list_for_broker(
                broker_name=(
                    self._broker.name
                ),
                limit=self._limit,
            )
        )

        local_open_orders = (
            self._repository
            .list_open_for_broker(
                broker_name=(
                    self._broker.name
                ),
                limit=self._limit,
            )
        )

        local_by_broker_id = {
            order.broker_order_id: order
            for order in local_orders
            if order.broker_order_id
        }

        matched = 0
        synchronized = 0
        refreshed = 0
        recovered = 0

        broker_only: list[
            BrokerOnlyOrder
        ] = []

        for snapshot in remote_orders:
            order = (
                local_by_broker_id
                .get(
                    snapshot
                    .broker_order_id
                )
            )

            if order is None:
                recovery_result = (
                    self._try_recover(
                        snapshot=snapshot
                    )
                )

                if (
                    recovery_result
                    is not None
                    and (
                        recovery_result
                        .recovered
                    )
                ):
                    recovered += 1
                    matched += 1
                    synchronized += 1
                    continue

                reason = (
                    "No local FinAI "
                    "order matched."
                )

                if recovery_result is not None:
                    reason = (
                        recovery_result
                        .reason
                    )

                broker_only.append(
                    self._to_broker_only(
                        snapshot,
                        reason=reason,
                    )
                )

                continue

            matched += 1

            if self._needs_sync(
                order=order,
                snapshot=snapshot,
            ):
                (
                    self._execution_service
                    .sync_from_snapshot(
                        order=order,
                        snapshot=snapshot,
                        source=(
                            "broker_discovery"
                        ),
                    )
                )

                synchronized += 1

            else:
                (
                    self._repository
                    .touch_synced(
                        order
                    )
                )

                refreshed += 1

        remote_open_ids = {
            snapshot.broker_order_id
            for snapshot
            in remote_open_orders
        }

        remote_open_truncated = (
            len(remote_open_orders)
            >= self._limit
        )

        missing_local_ids: list[
            UUID
        ] = []

        if not remote_open_truncated:
            for order in (
                local_open_orders
            ):
                broker_order_id = (
                    order.broker_order_id
                )

                if not broker_order_id:
                    continue

                if (
                    broker_order_id
                    not in remote_open_ids
                ):
                    missing_local_ids.append(
                        order.id
                    )

        return (
            AlpacaOrderDiscoveryResult(
                remote_orders=len(
                    remote_orders
                ),
                remote_open_orders=len(
                    remote_open_orders
                ),
                local_orders=len(
                    local_orders
                ),
                matched=matched,
                synchronized=(
                    synchronized
                ),
                refreshed=refreshed,
                recovered=recovered,
                broker_only=tuple(
                    broker_only
                ),
                local_open_missing_remote=(
                    tuple(
                        missing_local_ids
                    )
                ),
                remote_open_truncated=(
                    remote_open_truncated
                ),
            )
        )

    def _try_recover(
        self,
        *,
        snapshot: AlpacaOrderSnapshot,
    ):
        if (
            self._orphan_recovery_service
            is None
        ):
            return None

        return (
            self._orphan_recovery_service
            .recover(
                snapshot=snapshot
            )
        )

    @staticmethod
    def _needs_sync(
        *,
        order,
        snapshot: AlpacaOrderSnapshot,
    ) -> bool:
        local_filled = float(
            order.filled_quantity
            or 0.0
        )

        local_average = (
            order.average_fill_price
        )

        if (
            order.status
            != snapshot.status.value
        ):
            return True

        if (
            local_filled
            != snapshot
            .filled_quantity
        ):
            return True

        if (
            snapshot
            .average_fill_price
            is None
        ):
            return (
                local_average
                is not None
            )

        if local_average is None:
            return True

        return (
            float(local_average)
            != float(
                snapshot
                .average_fill_price
            )
        )

    @staticmethod
    def _to_broker_only(
        snapshot: AlpacaOrderSnapshot,
        *,
        reason: str,
    ) -> BrokerOnlyOrder:
        return BrokerOnlyOrder(
            broker_order_id=(
                snapshot
                .broker_order_id
            ),
            client_order_id=(
                snapshot
                .client_order_id
            ),
            symbol=(
                snapshot.symbol
            ),
            status=(
                snapshot.raw_status
            ),
            reason=reason,
        )