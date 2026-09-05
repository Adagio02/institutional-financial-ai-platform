from uuid import UUID

from sqlalchemy.orm import Session

from finai.domain.strategy.worker_enums import (
    StrategyWorkerStatus,
)
from finai.domain.strategy.worker_health import (
    is_worker_stale,
)
from finai.infrastructure.database.repositories.strategy_worker_repository import (
    StrategyWorkerRepository,
)


class StrategyWorkerRegistryService:
    def __init__(
        self,
        *,
        session: Session,
        stale_after_seconds: int,
    ) -> None:
        self._repository = (
            StrategyWorkerRepository(
                session
            )
        )

        self._stale_after_seconds = (
            stale_after_seconds
        )

    def register(
        self,
        *,
        worker_id: str,
        hostname: str,
        process_id: int,
    ):
        normalized_worker_id = worker_id.strip()

        if not normalized_worker_id:
            raise ValueError(
                "worker_id cannot be blank."
            )

        existing = (
            self._repository.get_by_worker_id(
                normalized_worker_id
            )
        )

        if existing is not None:
            raise ValueError(
                f"Worker already exists: {normalized_worker_id}"
            )

        worker = self._repository.create(
            worker_id=normalized_worker_id,
            hostname=hostname,
            process_id=process_id,
        )

        return self._repository.mark_running(
            worker
        )

    def heartbeat(
        self,
        *,
        worker_record_id: UUID,
    ):
        worker = self._repository.get_by_id(
            worker_record_id
        )

        if worker is None:
            raise LookupError(
                f"Strategy worker not found: {worker_record_id}"
            )

        return self._repository.heartbeat(
            worker
        )

    def record_results(
        self,
        *,
        worker_record_id: UUID,
        processed: int,
        successful: int,
        failed: int,
    ):
        worker = self._repository.get_by_id(
            worker_record_id
        )

        if worker is None:
            raise LookupError(
                f"Strategy worker not found: {worker_record_id}"
            )

        return self._repository.add_counts(
            worker,
            processed=processed,
            successful=successful,
            failed=failed,
        )

    def mark_stopping(
        self,
        *,
        worker_record_id: UUID,
    ):
        worker = self._repository.get_by_id(
            worker_record_id
        )

        if worker is None:
            raise LookupError(
                f"Strategy worker not found: {worker_record_id}"
            )

        return self._repository.mark_stopping(
            worker
        )

    def mark_stopped(
        self,
        *,
        worker_record_id: UUID,
    ):
        worker = self._repository.get_by_id(
            worker_record_id
        )

        if worker is None:
            raise LookupError(
                f"Strategy worker not found: {worker_record_id}"
            )

        return self._repository.mark_stopped(
            worker
        )

    def mark_failed(
        self,
        *,
        worker_record_id: UUID,
        error_message: str,
    ):
        worker = self._repository.get_by_id(
            worker_record_id
        )

        if worker is None:
            raise LookupError(
                f"Strategy worker not found: {worker_record_id}"
            )

        return self._repository.mark_failed(
            worker,
            error_message=error_message,
        )

    def list_workers(
        self,
        *,
        now,
    ):
        workers = self._repository.list_all()

        for worker in workers:
            if worker.status not in {
                StrategyWorkerStatus.RUNNING.value,
                StrategyWorkerStatus.STARTING.value,
            }:
                continue

            if is_worker_stale(
                last_heartbeat_at=(
                    worker.last_heartbeat_at
                ),
                now=now,
                stale_after_seconds=(
                    self._stale_after_seconds
                ),
            ):
                self._repository.mark_stale(
                    worker
                )

        return self._repository.list_all()