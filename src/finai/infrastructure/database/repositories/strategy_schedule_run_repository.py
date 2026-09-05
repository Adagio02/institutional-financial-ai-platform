from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.domain.strategy.schedule_enums import (
    StrategyScheduleRunStatus,
)
from finai.infrastructure.database.models.strategy_schedule_run import (
    StrategyScheduleRunModel,
)


class StrategyScheduleRunRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def create_started(
        self,
        *,
        schedule_id: UUID,
    ) -> StrategyScheduleRunModel:
        model = StrategyScheduleRunModel(
            schedule_id=schedule_id,
            status=StrategyScheduleRunStatus.STARTED.value,
        )

        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)

        return model

    def mark_completed(
        self,
        model: StrategyScheduleRunModel,
        *,
        strategy_run_id: UUID,
    ) -> StrategyScheduleRunModel:
        model.strategy_run_id = strategy_run_id
        model.status = (
            StrategyScheduleRunStatus.COMPLETED.value
        )
        model.error_message = None
        model.completed_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(model)

        return model

    def mark_failed(
        self,
        model: StrategyScheduleRunModel,
        *,
        error_message: str,
    ) -> StrategyScheduleRunModel:
        model.status = (
            StrategyScheduleRunStatus.FAILED.value
        )
        model.error_message = error_message
        model.completed_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(model)

        return model

    def list_for_schedule(
        self,
        *,
        schedule_id: UUID,
    ) -> list[StrategyScheduleRunModel]:
        statement = (
            select(StrategyScheduleRunModel)
            .where(
                StrategyScheduleRunModel.schedule_id
                == schedule_id
            )
            .order_by(
                StrategyScheduleRunModel.created_at.desc()
            )
        )

        return list(
            self._session.scalars(statement).all()
        )