from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.domain.strategy.enums import (
    TradeProposalStatus,
)
from finai.infrastructure.database.models.trade_proposal import (
    TradeProposalModel,
)


class TradeProposalRepository:
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
        source_model_id: UUID | None,
        source_prediction_id: UUID | None,
        symbol: str,
        side: str,
        confidence: float,
        quantity: float,
        proposed_notional: float,
        allocation_fraction: float,
        reference_price: float,
        reference_price_timestamp: datetime,
        reference_price_provider: str,
        status: TradeProposalStatus,
        rejection_reason: str | None = None,
    ) -> TradeProposalModel:
        proposal = TradeProposalModel(
            account_id=account_id,
            instrument_id=instrument_id,
            source_model_id=(source_model_id),
            source_prediction_id=(source_prediction_id),
            symbol=symbol.strip().upper(),
            side=side,
            confidence=confidence,
            quantity=quantity,
            proposed_notional=(proposed_notional),
            allocation_fraction=(allocation_fraction),
            reference_price=(reference_price),
            reference_price_timestamp=(reference_price_timestamp),
            reference_price_provider=(reference_price_provider),
            status=status.value,
            rejection_reason=(rejection_reason),
        )

        self._session.add(proposal)
        self._session.commit()
        self._session.refresh(proposal)

        return proposal

    def get_by_id(
        self,
        proposal_id: UUID,
    ) -> TradeProposalModel | None:
        return self._session.get(
            TradeProposalModel,
            proposal_id,
        )

    def list_for_account(
        self,
        account_id: UUID,
    ) -> list[TradeProposalModel]:
        statement = (
            select(TradeProposalModel)
            .where(TradeProposalModel.account_id == account_id)
            .order_by(TradeProposalModel.created_at.desc())
        )

        return list(self._session.scalars(statement).all())

    def mark_approved(
        self,
        proposal: TradeProposalModel,
        *,
        reason: str | None,
    ) -> TradeProposalModel:
        proposal.status = TradeProposalStatus.APPROVED.value

        proposal.approved_at = datetime.now(UTC)

        proposal.rejected_at = None
        proposal.rejection_reason = None
        proposal.decision_reason = reason

        self._session.commit()
        self._session.refresh(proposal)

        return proposal

    def mark_rejected(
        self,
        proposal: TradeProposalModel,
        *,
        reason: str,
    ) -> TradeProposalModel:
        proposal.status = TradeProposalStatus.REJECTED.value

        proposal.rejected_at = datetime.now(UTC)

        proposal.rejection_reason = reason
        proposal.decision_reason = reason

        self._session.commit()
        self._session.refresh(proposal)

        return proposal

    def mark_executed(
        self,
        proposal: TradeProposalModel,
        *,
        order_id: UUID,
    ) -> TradeProposalModel:
        proposal.status = TradeProposalStatus.EXECUTED.value

        proposal.order_id = order_id

        proposal.executed_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(proposal)

        return proposal

    def mark_execution_rejected(
        self,
        proposal: TradeProposalModel,
        *,
        order_id: UUID | None,
        reason: str,
    ) -> TradeProposalModel:
        proposal.status = TradeProposalStatus.EXECUTION_REJECTED.value

        proposal.order_id = order_id
        proposal.rejection_reason = reason

        self._session.commit()
        self._session.refresh(proposal)

        return proposal

    def mark_expired(
        self,
        proposal: TradeProposalModel,
        *,
        reason: str,
    ) -> TradeProposalModel:
        proposal.status = TradeProposalStatus.EXPIRED.value

        proposal.rejection_reason = reason

        self._session.commit()
        self._session.refresh(proposal)

        return proposal
