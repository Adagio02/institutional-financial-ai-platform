from datetime import (
    UTC,
    datetime,
    timedelta,
)
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
            failure_count=0,
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
            select(
                StrategyScheduleModel
            )
            .where(
                StrategyScheduleModel.account_id
                == account_id
            )
            .order_by(
                StrategyScheduleModel
                .created_at
                .desc()
            )
        )

        return list(
            self._session.scalars(
                statement
            ).all()
        )

    def list_due(
        self,
        *,
        now: datetime,
    ) -> list[StrategyScheduleModel]:
        statement = (
            select(
                StrategyScheduleModel
            )
            .where(
                StrategyScheduleModel.enabled
                .is_(True),
                or_(
                    StrategyScheduleModel.next_run_at
                    .is_(None),
                    StrategyScheduleModel.next_run_at
                    <= now,
                ),
                or_(
                    StrategyScheduleModel.retry_at
                    .is_(None),
                    StrategyScheduleModel.retry_at
                    <= now,
                ),
            )
            .order_by(
                StrategyScheduleModel
                .next_run_at
                .asc()
            )
        )

        return list(
            self._session.scalars(
                statement
            ).all()
        )

    def claim_due(
        self,
        *,
        now: datetime,
        worker_id: str,
        lease_seconds: int,
        limit: int,
    ) -> list[StrategyScheduleModel]:
        if not worker_id.strip():
            raise ValueError(
                "worker_id cannot be blank."
            )

        if lease_seconds <= 0:
            raise ValueError(
                "lease_seconds must be greater than zero."
            )

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero."
            )

        statement = (
            select(
                StrategyScheduleModel
            )
            .where(
                StrategyScheduleModel.enabled
                .is_(True),
                or_(
                    StrategyScheduleModel.next_run_at
                    .is_(None),
                    StrategyScheduleModel.next_run_at
                    <= now,
                ),
                or_(
                    StrategyScheduleModel.retry_at
                    .is_(None),
                    StrategyScheduleModel.retry_at
                    <= now,
                ),
                or_(
                    StrategyScheduleModel.lease_expires_at
                    .is_(None),
                    StrategyScheduleModel.lease_expires_at
                    <= now,
                ),
            )
            .order_by(
                StrategyScheduleModel
                .next_run_at
                .asc()
            )
            .with_for_update(
                skip_locked=True
            )
            .limit(limit)
        )

        schedules = list(
            self._session.scalars(
                statement
            ).all()
        )

        lease_expires_at = (
            now
            + timedelta(
                seconds=lease_seconds
            )
        )

        for schedule in schedules:
            schedule.lease_owner = worker_id
            schedule.lease_expires_at = (
                lease_expires_at
            )

        self._session.commit()

        for schedule in schedules:
            self._session.refresh(schedule)

        return schedules

    def set_enabled(
        self,
        model: StrategyScheduleModel,
        *,
        enabled: bool,
    ) -> StrategyScheduleModel:
        model.enabled = enabled
        model.updated_at = datetime.now(UTC)

        if not enabled:
            model.lease_owner = None
            model.lease_expires_at = None

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

    def release_success(
        self,
        model: StrategyScheduleModel,
    ) -> StrategyScheduleModel:
        model.lease_owner = None
        model.lease_expires_at = None
        model.failure_count = 0
        model.retry_at = None
        model.last_error = None
        model.updated_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(model)

        return model

    def release_failure(
        self,
        model: StrategyScheduleModel,
        *,
        failure_count: int,
        retry_at: datetime | None,
        error_message: str,
        disable: bool,
    ) -> StrategyScheduleModel:
        model.lease_owner = None
        model.lease_expires_at = None
        model.failure_count = failure_count
        model.retry_at = retry_at
        model.last_error = error_message
        model.updated_at = datetime.now(UTC)

        if disable:
            model.enabled = False
            model.retry_at = None

        self._session.commit()
        self._session.refresh(model)

        return model

    def has_active_lease(
        self,
        *,
        model: StrategyScheduleModel,
        now: datetime,
        expected_owner: str | None,
    ) -> bool:
        if model.lease_expires_at is None:
            return False

        if model.lease_expires_at <= now:
            return False

        if expected_owner is None:
            return True

        return model.lease_owner != expected_owner