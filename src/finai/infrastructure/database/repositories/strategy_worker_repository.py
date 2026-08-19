from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.domain.strategy.worker_enums import (
    StrategyWorkerStatus,
)
from finai.infrastructure.database.models.strategy_worker import (
    StrategyWorkerModel,
)


class StrategyWorkerRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def create(
        self,
        *,
        worker_id: str,
        hostname: str,
        process_id: int,
    ) -> StrategyWorkerModel:
        model = StrategyWorkerModel(
            worker_id=worker_id,
            hostname=hostname,
            process_id=process_id,
            status=StrategyWorkerStatus.STARTING.value,
        )

        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)

        return model

    def get_by_id(
        self,
        worker_record_id: UUID,
    ) -> StrategyWorkerModel | None:
        return self._session.get(
            StrategyWorkerModel,
            worker_record_id,
        )

    def get_by_worker_id(
        self,
        worker_id: str,
    ) -> StrategyWorkerModel | None:
        statement = select(
            StrategyWorkerModel
        ).where(
            StrategyWorkerModel.worker_id
            == worker_id
        )

        return self._session.scalar(
            statement
        )

    def list_all(
        self,
    ) -> list[StrategyWorkerModel]:
        statement = (
            select(
                StrategyWorkerModel
            )
            .order_by(
                StrategyWorkerModel
                .last_heartbeat_at
                .desc()
            )
        )

        return list(
            self._session.scalars(
                statement
            ).all()
        )

    def mark_running(
        self,
        model: StrategyWorkerModel,
    ) -> StrategyWorkerModel:
        now = datetime.now(UTC)

        model.status = (
            StrategyWorkerStatus.RUNNING.value
        )

        model.last_heartbeat_at = now
        model.updated_at = now

        self._session.commit()
        self._session.refresh(model)

        return model

    def heartbeat(
        self,
        model: StrategyWorkerModel,
    ) -> StrategyWorkerModel:
        now = datetime.now(UTC)

        model.last_heartbeat_at = now
        model.updated_at = now

        if (
            model.status
            == StrategyWorkerStatus.STARTING.value
        ):
            model.status = (
                StrategyWorkerStatus.RUNNING.value
            )

        self._session.commit()
        self._session.refresh(model)

        return model

    def add_counts(
        self,
        model: StrategyWorkerModel,
        *,
        processed: int,
        successful: int,
        failed: int,
    ) -> StrategyWorkerModel:
        model.processed_count += processed
        model.successful_count += successful
        model.failed_count += failed
        model.updated_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(model)

        return model

    def mark_stopping(
        self,
        model: StrategyWorkerModel,
    ) -> StrategyWorkerModel:
        model.status = (
            StrategyWorkerStatus.STOPPING.value
        )

        model.updated_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(model)

        return model

    def mark_stopped(
        self,
        model: StrategyWorkerModel,
    ) -> StrategyWorkerModel:
        now = datetime.now(UTC)

        model.status = (
            StrategyWorkerStatus.STOPPED.value
        )

        model.stopped_at = now
        model.updated_at = now

        self._session.commit()
        self._session.refresh(model)

        return model

    def mark_failed(
        self,
        model: StrategyWorkerModel,
        *,
        error_message: str,
    ) -> StrategyWorkerModel:
        now = datetime.now(UTC)

        model.status = (
            StrategyWorkerStatus.FAILED.value
        )

        model.last_error = error_message
        model.stopped_at = now
        model.updated_at = now

        self._session.commit()
        self._session.refresh(model)

        return model

    def mark_stale(
        self,
        model: StrategyWorkerModel,
    ) -> StrategyWorkerModel:
        model.status = (
            StrategyWorkerStatus.STALE.value
        )

        model.updated_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(model)

        return model