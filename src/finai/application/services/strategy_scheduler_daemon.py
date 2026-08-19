import logging
import os
import socket
from datetime import UTC, datetime
from threading import Event
from uuid import uuid4

from sqlalchemy.orm import Session

from finai.application.services.strategy_schedule_worker_service import (
    StrategyScheduleWorkerService,
)
from finai.application.services.strategy_worker_registry_service import (
    StrategyWorkerRegistryService,
)
from finai.domain.strategy.worker_health import (
    validate_heartbeat_interval,
    validate_poll_interval,
)


logger = logging.getLogger(__name__)


class StrategySchedulerDaemon:
    def __init__(
        self,
        *,
        session: Session,
        worker_service: StrategyScheduleWorkerService,
        registry_service: StrategyWorkerRegistryService,
        poll_interval_seconds: int,
        heartbeat_interval_seconds: int,
        stale_after_seconds: int,
        shutdown_event: Event | None = None,
    ) -> None:
        validate_poll_interval(
            poll_interval_seconds=(
                poll_interval_seconds
            )
        )

        validate_heartbeat_interval(
            heartbeat_interval_seconds=(
                heartbeat_interval_seconds
            ),
            stale_after_seconds=(
                stale_after_seconds
            ),
        )

        self._session = session

        self._worker_service = (
            worker_service
        )

        self._registry_service = (
            registry_service
        )

        self._poll_interval_seconds = (
            poll_interval_seconds
        )

        self._heartbeat_interval_seconds = (
            heartbeat_interval_seconds
        )

        self._shutdown_event = (
            shutdown_event or Event()
        )

    @staticmethod
    def build_worker_id() -> str:
        hostname = socket.gethostname()

        return (
            f"{hostname}-"
            f"{os.getpid()}-"
            f"{uuid4().hex[:8]}"
        )

    def request_shutdown(
        self,
    ) -> None:
        self._shutdown_event.set()

    def run(
        self,
    ) -> None:
        worker_id = self.build_worker_id()

        worker = (
            self._registry_service.register(
                worker_id=worker_id,
                hostname=socket.gethostname(),
                process_id=os.getpid(),
            )
        )

        last_heartbeat = datetime.now(UTC)

        logger.info(
            "Strategy scheduler started. worker_id=%s",
            worker_id,
        )

        try:
            while not self._shutdown_event.is_set():
                results = (
                    self._worker_service.process_due(
                        worker_id=worker_id
                    )
                )

                successful = sum(
                    1
                    for result in results
                    if result.status == "completed"
                )

                failed = sum(
                    1
                    for result in results
                    if result.status == "failed"
                )

                if results:
                    (
                        self._registry_service
                        .record_results(
                            worker_record_id=worker.id,
                            processed=len(results),
                            successful=successful,
                            failed=failed,
                        )
                    )

                now = datetime.now(UTC)

                heartbeat_age = (
                    now - last_heartbeat
                ).total_seconds()

                if (
                    heartbeat_age
                    >= self._heartbeat_interval_seconds
                ):
                    (
                        self._registry_service
                        .heartbeat(
                            worker_record_id=worker.id
                        )
                    )

                    last_heartbeat = now

                self._shutdown_event.wait(
                    self._poll_interval_seconds
                )

            (
                self._registry_service
                .mark_stopping(
                    worker_record_id=worker.id
                )
            )

            (
                self._registry_service
                .mark_stopped(
                    worker_record_id=worker.id
                )
            )

            logger.info(
                "Strategy scheduler stopped. worker_id=%s",
                worker_id,
            )

        except Exception as error:
            logger.exception(
                "Strategy scheduler failed."
            )

            try:
                (
                    self._registry_service
                    .mark_failed(
                        worker_record_id=worker.id,
                        error_message=str(error),
                    )
                )

            finally:
                raise

        finally:
            self._session.rollback()