from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.domain.strategy.run_enums import (
    StrategyRunItemStatus,
)
from finai.infrastructure.database.models.strategy_run_item import (
    StrategyRunItemModel,
)


class StrategyRunItemRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def create(
        self,
        *,
        strategy_run_id: UUID,
        sequence_number: int,
        symbol: str,
        side: str,
        confidence: float,
        source_model_id: UUID | None,
        source_prediction_id: UUID | None,
    ) -> StrategyRunItemModel:
        model = StrategyRunItemModel(
            strategy_run_id=(strategy_run_id),
            sequence_number=(sequence_number),
            symbol=symbol.strip().upper(),
            side=side,
            confidence=confidence,
            source_model_id=(source_model_id),
            source_prediction_id=(source_prediction_id),
            status=(StrategyRunItemStatus.PENDING.value),
        )

        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)

        return model

    def list_for_run(
        self,
        *,
        strategy_run_id: UUID,
    ) -> list[StrategyRunItemModel]:
        statement = (
            select(StrategyRunItemModel)
            .where(StrategyRunItemModel.strategy_run_id == strategy_run_id)
            .order_by(StrategyRunItemModel.sequence_number)
        )

        return list(self._session.scalars(statement).all())

    def mark_proposal_created(
        self,
        model: StrategyRunItemModel,
        *,
        proposal_id: UUID,
    ) -> StrategyRunItemModel:
        model.proposal_id = proposal_id

        model.status = StrategyRunItemStatus.PROPOSAL_CREATED.value

        model.error_message = None

        model.completed_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(model)

        return model

    def mark_failed(
        self,
        model: StrategyRunItemModel,
        *,
        error_message: str,
    ) -> StrategyRunItemModel:
        model.status = StrategyRunItemStatus.FAILED.value

        model.error_message = error_message

        model.completed_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(model)

        return model
