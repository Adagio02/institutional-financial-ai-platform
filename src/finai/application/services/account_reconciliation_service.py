from uuid import UUID

from sqlalchemy.orm import Session

from finai.infrastructure.database.repositories.execution_audit_repository import (
    ExecutionAuditRepository,
)
from finai.infrastructure.database.repositories.paper_account_repository import (
    PaperAccountRepository,
)
from finai.infrastructure.database.repositories.paper_position_repository import (
    PaperPositionRepository,
)


class AccountReconciliationService:
    def __init__(
        self,
        *,
        session: Session,
    ) -> None:
        self._account_repository = PaperAccountRepository(session)

        self._position_repository = PaperPositionRepository(session)

        self._audit_repository = ExecutionAuditRepository(session)

    def reconcile(
        self,
        *,
        account_id: UUID,
    ) -> dict:
        account = self._account_repository.get_by_id(account_id)

        if account is None:
            raise LookupError(f"Paper account not found: {account_id}")

        positions = self._position_repository.list_for_account(account_id)

        results: list[dict] = []

        issue_count = 0

        for position in positions:
            issue: str | None = None

            if position.quantity == 0 and position.average_price != 0:
                issue = "Flat position has a non-zero average price."

            elif position.quantity != 0 and position.average_price <= 0:
                issue = "Open position has an invalid average price."

            if issue is not None:
                issue_count += 1

            results.append(
                {
                    "instrument_id": (position.instrument_id),
                    "symbol": (position.symbol),
                    "quantity": (position.quantity),
                    "average_price": (position.average_price),
                    "issue": issue,
                }
            )

        healthy = issue_count == 0

        self._audit_repository.create(
            account_id=account.id,
            event_type=("account_reconciliation"),
            message=("Paper account reconciliation completed."),
            event_data={
                "healthy": healthy,
                "issue_count": issue_count,
                "position_count": (len(positions)),
            },
        )

        return {
            "account_id": account.id,
            "cash": account.cash,
            "realized_pnl": (account.realized_pnl),
            "position_count": (len(positions)),
            "issue_count": issue_count,
            "healthy": healthy,
            "positions": results,
        }
