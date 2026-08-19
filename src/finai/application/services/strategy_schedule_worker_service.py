from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from finai.application.services.strategy_schedule_service import (
    StrategyScheduleService,
)
from finai.domain.strategy.schedule_retry import (
    calculate_retry_at,
)
from finai.infrastructure.database.repositories.strategy_schedule_repository import (
    StrategyScheduleRepository,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ScheduleWorkerResult:
    schedule_id: UUID
    status: str
    strategy_run_id: UUID | None
    error_message: str | None


class StrategyScheduleWorkerService:
    def __init__(
        self,
        *,
        session: Session,
        schedule_service: StrategyScheduleService,
        lease_seconds: int,
        batch_size: int,
        retry_base_seconds: int,
        retry_maximum_seconds: int,
        maximum_failures: int,
    ) -> None:
        self._repository = (
            StrategyScheduleRepository(
                session
            )
        )

        self._schedule_service = (
            schedule_service
        )

        self._lease_seconds = lease_seconds
        self._batch_size = batch_size

        self._retry_base_seconds = (
            retry_base_seconds
        )

        self._retry_maximum_seconds = (
            retry_maximum_seconds
        )

        self._maximum_failures = (
            maximum_failures
        )

    def process_due(
        self,
        *,
        worker_id: str,
    ) -> list[ScheduleWorkerResult]:
        normalized_worker_id = (
            worker_id.strip()
        )

        if not normalized_worker_id:
            raise ValueError(
                "worker_id cannot be blank."
            )

        now = datetime.now(UTC)

        schedules = (
            self._repository.claim_due(
                now=now,
                worker_id=(
                    normalized_worker_id
                ),
                lease_seconds=(
                    self._lease_seconds
                ),
                limit=self._batch_size,
            )
        )

        results: list[
            ScheduleWorkerResult
        ] = []

        for schedule in schedules:
            try:
                strategy_run = (
                    self._schedule_service.run(
                        schedule_id=schedule.id,
                        lease_owner=(
                            normalized_worker_id
                        ),
                    )
                )

            except Exception as error:  # noqa: BLE001
                failure_count = (
                    schedule.failure_count
                    + 1
                )

                disable = (
                    failure_count
                    >= self._maximum_failures
                )

                retry_at = None

                if not disable:
                    retry_at = (
                        calculate_retry_at(
                            now=datetime.now(UTC),
                            failure_count=(
                                failure_count
                            ),
                            base_delay_seconds=(
                                self._retry_base_seconds
                            ),
                            maximum_delay_seconds=(
                                self._retry_maximum_seconds
                            ),
                        )
                    )

                self._repository.release_failure(
                    schedule,
                    failure_count=(
                        failure_count
                    ),
                    retry_at=retry_at,
                    error_message=str(error),
                    disable=disable,
                )

                results.append(
                    ScheduleWorkerResult(
                        schedule_id=(
                            schedule.id
                        ),
                        status="failed",
                        strategy_run_id=None,
                        error_message=str(
                            error
                        ),
                    )
                )

                continue

            self._repository.release_success(
                schedule
            )

            results.append(
                ScheduleWorkerResult(
                    schedule_id=schedule.id,
                    status="completed",
                    strategy_run_id=(
                        strategy_run.id
                    ),
                    error_message=None,
                )
            )

        return results