from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import (
    or_,
    select,
)
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.strategy_schedule import (
    StrategyScheduleModel,
)


class StrategyScheduleRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def create(
        self,
        *,
        account_id: UUID,
        strategy_key: str,
        name: str,
        frequency: str,
        enabled: bool,
        next_run_at: datetime | None,
    ) -> StrategyScheduleModel:
        model = StrategyScheduleModel(
            account_id=account_id,
            strategy_key=strategy_key,
            name=name,
            frequency=frequency,
            enabled=enabled,
            next_run_at=next_run_at,
        )

        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)

        return model

    def get_by_id(
        self,
        schedule_id: UUID,
    ) -> StrategyScheduleModel | None:
        return self._session.get(
            StrategyScheduleModel,
            schedule_id,
        )

    def list_for_account(
        self,
        *,
        account_id: UUID,
    ) -> list[StrategyScheduleModel]:
        statement = (
            select(StrategyScheduleModel)
            .where(
                StrategyScheduleModel.account_id == account_id
            )
            .order_by(
                StrategyScheduleModel.created_at.desc()
            )
        )

        return list(
            self._session.scalars(statement).all()
        )

    def list_due(
        self,
        *,
        now: datetime,
    ) -> list[StrategyScheduleModel]:
        statement = (
            select(StrategyScheduleModel)
            .where(
                StrategyScheduleModel.enabled.is_(True),
                or_(
                    StrategyScheduleModel.next_run_at.is_(None),
                    StrategyScheduleModel.next_run_at <= now,
                ),
            )
            .order_by(
                StrategyScheduleModel.next_run_at.asc()
            )
        )

        return list(
            self._session.scalars(statement).all()
        )

    def set_enabled(
        self,
        model: StrategyScheduleModel,
        *,
        enabled: bool,
    ) -> StrategyScheduleModel:
        model.enabled = enabled
        model.updated_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(model)

        return model

    def update_after_run(
        self,
        model: StrategyScheduleModel,
        *,
        completed_at: datetime,
        next_run_at: datetime,
    ) -> StrategyScheduleModel:
        model.last_run_at = completed_at
        model.next_run_at = next_run_at
        model.updated_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(model)

        return model