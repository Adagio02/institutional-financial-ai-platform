from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from finai.application.services.alpaca_order_execution_service import (
    AlpacaOrderExecutionService,
)
from finai.infrastructure.database.repositories.order_repository import (
    OrderRepository,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AlpacaReconciliationFailure:
    order_id: UUID

    broker_order_id: str

    error_message: str


@dataclass(
    frozen=True,
    slots=True,
)
class AlpacaReconciliationResult:
    scanned: int

    synchronized: int

    failed: int

    failures: tuple[
        AlpacaReconciliationFailure,
        ...,
    ]


class AlpacaReconciliationService:
    def __init__(
        self,
        *,
        session: Session,
        execution_service: (
            AlpacaOrderExecutionService
        ),
        batch_size: int,
        broker_name: str = (
            "alpaca-paper"
        ),
    ) -> None:
        if batch_size <= 0:
            raise ValueError(
                "batch_size must be "
                "positive."
            )

        normalized_broker_name = (
            broker_name.strip()
        )

        if not normalized_broker_name:
            raise ValueError(
                "broker_name cannot "
                "be blank."
            )

        self._session = session

        self._repository = (
            OrderRepository(
                session
            )
        )

        self._execution_service = (
            execution_service
        )

        self._batch_size = (
            batch_size
        )

        self._broker_name = (
            normalized_broker_name
        )

    def reconcile_open_orders(
        self,
    ) -> AlpacaReconciliationResult:
        orders = (
            self._repository
            .list_open_for_broker(
                broker_name=(
                    self._broker_name
                ),
                limit=(
                    self._batch_size
                ),
            )
        )

        synchronized = 0

        failures: list[
            AlpacaReconciliationFailure
        ] = []

        for order in orders:
            try:
                (
                    self._execution_service
                    .sync(
                        order=order
                    )
                )

                synchronized += 1

            except Exception as error:  # noqa: BLE001
                self._session.rollback()

                failures.append(
                    AlpacaReconciliationFailure(
                        order_id=order.id,
                        broker_order_id=(
                            order.broker_order_id
                            or ""
                        ),
                        error_message=(
                            str(error)
                        ),
                    )
                )

        return AlpacaReconciliationResult(
            scanned=len(
                orders
            ),
            synchronized=(
                synchronized
            ),
            failed=len(
                failures
            ),
            failures=tuple(
                failures
            ),
        )