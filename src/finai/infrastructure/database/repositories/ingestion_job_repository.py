from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from finai.infrastructure.database.models.ingestion_job import (
    IngestionJobModel,
)


class IngestionJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
    ) -> IngestionJobModel:
        job = IngestionJobModel(
            symbol=symbol.strip().upper(),
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            status="pending",
            received_count=0,
            inserted_count=0,
        )

        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)

        return job

    def get_by_id(
        self,
        job_id: UUID,
    ) -> IngestionJobModel | None:
        return self._session.get(IngestionJobModel, job_id)

    def mark_running(
        self,
        job: IngestionJobModel,
    ) -> IngestionJobModel:
        job.status = "running"
        job.started_at = datetime.now(UTC)
        job.completed_at = None
        job.error_message = None

        self._session.commit()
        self._session.refresh(job)

        return job

    def mark_completed(
        self,
        job: IngestionJobModel,
        *,
        received_count: int,
        inserted_count: int,
    ) -> IngestionJobModel:
        job.status = "completed"
        job.received_count = received_count
        job.inserted_count = inserted_count
        job.completed_at = datetime.now(UTC)
        job.error_message = None

        self._session.commit()
        self._session.refresh(job)

        return job

    def mark_failed(
        self,
        job: IngestionJobModel,
        *,
        error_message: str,
    ) -> IngestionJobModel:
        job.status = "failed"
        job.error_message = error_message[:4000]
        job.completed_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(job)

        return job
