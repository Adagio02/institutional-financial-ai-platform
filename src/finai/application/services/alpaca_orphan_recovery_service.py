from __future__ import annotations

from dataclasses import dataclass
from uuid import (
    UUID,
)

from sqlalchemy.orm import Session

from finai.application.services.alpaca_order_execution_service import (
    AlpacaOrderExecutionService,
)
from finai.infrastructure.database.repositories.execution_audit_repository import (
    ExecutionAuditRepository,
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
class AlpacaOrphanRecoveryResult:
    recovered: bool

    order_id: UUID | None

    reason: str


class AlpacaOrphanRecoveryService:
    def __init__(
        self,
        *,
        session: Session,
        broker: AlpacaPaperBroker,
        execution_service: (
            AlpacaOrderExecutionService
        ),
        require_symbol_match: bool,
        require_quantity_match: bool,
    ) -> None:
        self._repository = (
            OrderRepository(
                session
            )
        )

        self._audit_repository = (
            ExecutionAuditRepository(
                session
            )
        )

        self._broker = broker

        self._execution_service = (
            execution_service
        )

        self._require_symbol_match = (
            require_symbol_match
        )

        self._require_quantity_match = (
            require_quantity_match
        )

    def recover(
        self,
        *,
        snapshot: AlpacaOrderSnapshot,
    ) -> AlpacaOrphanRecoveryResult:
        if (
            self._repository
            .get_by_broker_order_id(
                snapshot
                .broker_order_id
            )
            is not None
        ):
            return (
                AlpacaOrphanRecoveryResult(
                    recovered=False,
                    order_id=None,
                    reason=(
                        "Broker order is "
                        "already linked."
                    ),
                )
            )

        candidate = (
            self._find_candidate(
                snapshot=snapshot
            )
        )

        if candidate is None:
            return (
                AlpacaOrphanRecoveryResult(
                    recovered=False,
                    order_id=None,
                    reason=(
                        "No unambiguous local "
                        "FinAI order matched."
                    ),
                )
            )

        validation_error = (
            self._validate_candidate(
                order=candidate,
                snapshot=snapshot,
            )
        )

        if validation_error is not None:
            return (
                AlpacaOrphanRecoveryResult(
                    recovered=False,
                    order_id=(
                        candidate.id
                    ),
                    reason=(
                        validation_error
                    ),
                )
            )

        linked = (
            self._repository
            .attach_broker_identity(
                candidate,
                broker_order_id=(
                    snapshot
                    .broker_order_id
                ),
                broker_name=(
                    self._broker.name
                ),
            )
        )

        self._audit_repository.create(
            account_id=(
                linked.account_id
            ),
            order_id=linked.id,
            event_type=(
                "alpaca_orphan_recovered"
            ),
            message=(
                "Recovered missing Alpaca "
                "broker-order linkage."
            ),
            event_data={
                "broker_order_id": (
                    snapshot
                    .broker_order_id
                ),
                "client_order_id": (
                    snapshot
                    .client_order_id
                ),
                "symbol": (
                    snapshot.symbol
                ),
            },
        )

        (
            self._execution_service
            .sync_from_snapshot(
                order=linked,
                snapshot=snapshot,
                source=(
                    "orphan_recovery"
                ),
            )
        )

        return (
            AlpacaOrphanRecoveryResult(
                recovered=True,
                order_id=linked.id,
                reason="recovered",
            )
        )

    def _find_candidate(
        self,
        *,
        snapshot: AlpacaOrderSnapshot,
    ):
        client_order_id = (
            snapshot.client_order_id
        )

        if not client_order_id:
            return None

        normalized = (
            client_order_id.strip()
        )

        if not normalized:
            return None

        finai_order_id = (
            self._parse_finai_order_id(
                normalized
            )
        )

        if finai_order_id is not None:
            candidate = (
                self._repository
                .get_by_id(
                    finai_order_id
                )
            )

            if candidate is not None:
                return candidate

        candidates = (
            self._repository
            .list_by_client_order_id(
                normalized
            )
        )

        if len(candidates) != 1:
            return None

        return candidates[0]

    def _validate_candidate(
        self,
        *,
        order,
        snapshot: AlpacaOrderSnapshot,
    ) -> str | None:
        if order.broker_order_id:
            return (
                "Local order already has "
                "a broker order ID."
            )

        if order.broker_name:
            return (
                "Local order already has "
                "a broker name."
            )

        if (
            self._require_symbol_match
            and (
                order.symbol
                .strip()
                .upper()
                != snapshot.symbol
                .strip()
                .upper()
            )
        ):
            return (
                "Symbol mismatch prevented "
                "orphan recovery."
            )

        if (
            self._require_quantity_match
            and abs(
                float(order.quantity)
                - float(
                    snapshot
                    .requested_quantity
                )
            )
            > 1e-9
        ):
            return (
                "Quantity mismatch prevented "
                "orphan recovery."
            )

        if (
            snapshot.side is not None
            and (
                str(order.side)
                .strip()
                .lower()
                != snapshot.side
            )
        ):
            return (
                "Side mismatch prevented "
                "orphan recovery."
            )

        if (
            snapshot.order_type
            is not None
            and (
                str(order.order_type)
                .strip()
                .lower()
                != snapshot.order_type
            )
        ):
            return (
                "Order-type mismatch prevented "
                "orphan recovery."
            )

        if (
            snapshot.time_in_force
            is not None
            and (
                str(order.time_in_force)
                .strip()
                .lower()
                != snapshot.time_in_force
            )
        ):
            return (
                "Time-in-force mismatch "
                "prevented orphan recovery."
            )

        return None

    @staticmethod
    def _parse_finai_order_id(
        client_order_id: str,
    ) -> UUID | None:
        prefix = "finai-"

        if not (
            client_order_id
            .lower()
            .startswith(
                prefix
            )
        ):
            return None

        raw_id = (
            client_order_id[
                len(prefix):
            ]
        )

        try:
            return UUID(
                raw_id
            )

        except ValueError:
            return None