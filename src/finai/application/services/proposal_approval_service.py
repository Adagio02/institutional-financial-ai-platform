from uuid import UUID

from sqlalchemy.orm import Session

from finai.domain.strategy.enums import (
    TradeProposalStatus,
)
from finai.infrastructure.database.repositories.execution_audit_repository import (
    ExecutionAuditRepository,
)
from finai.infrastructure.database.repositories.trade_proposal_repository import (
    TradeProposalRepository,
)


class ProposalApprovalService:
    def __init__(
        self,
        *,
        session: Session,
    ) -> None:
        self._proposal_repository = TradeProposalRepository(session)

        self._audit_repository = ExecutionAuditRepository(session)

    def approve(
        self,
        *,
        proposal_id: UUID,
        reason: str | None,
    ):
        proposal = self._proposal_repository.get_by_id(proposal_id)

        if proposal is None:
            raise LookupError(f"Trade proposal not found: {proposal_id}")

        if proposal.status != TradeProposalStatus.PENDING_APPROVAL.value:
            raise ValueError("Only pending proposals can be approved.")

        approved = self._proposal_repository.mark_approved(
            proposal,
            reason=reason,
        )

        self._audit_repository.create(
            account_id=proposal.account_id,
            event_type=("trade_proposal_approved"),
            message=("Trade proposal was approved."),
            event_data={
                "proposal_id": (str(proposal.id)),
                "reason": reason,
            },
        )

        return approved

    def reject(
        self,
        *,
        proposal_id: UUID,
        reason: str,
    ):
        proposal = self._proposal_repository.get_by_id(proposal_id)

        if proposal is None:
            raise LookupError(f"Trade proposal not found: {proposal_id}")

        if proposal.status != TradeProposalStatus.PENDING_APPROVAL.value:
            raise ValueError("Only pending proposals can be rejected.")

        normalized_reason = reason.strip()

        if not normalized_reason:
            raise ValueError("A rejection reason is required.")

        rejected = self._proposal_repository.mark_rejected(
            proposal,
            reason=(normalized_reason),
        )

        self._audit_repository.create(
            account_id=proposal.account_id,
            event_type=("trade_proposal_rejected"),
            message=("Trade proposal was rejected."),
            event_data={
                "proposal_id": (str(proposal.id)),
                "reason": (normalized_reason),
            },
        )

        return rejected
