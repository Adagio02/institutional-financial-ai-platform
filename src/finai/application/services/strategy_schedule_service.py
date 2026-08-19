from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from finai.application.services.strategy_run_service import (
    StrategyRunService,
    StrategySignal,
)
from finai.domain.execution.enums import (
    OrderSide,
)
from finai.domain.strategy.schedule_calculator import (
    calculate_next_run_at,
)
from finai.domain.strategy.schedule_enums import (
    StrategyScheduleFrequency,
)
from finai.infrastructure.database.repositories.paper_account_repository import (
    PaperAccountRepository,
)
from finai.infrastructure.database.repositories.strategy_schedule_repository import (
    StrategyScheduleRepository,
)
from finai.infrastructure.database.repositories.strategy_schedule_run_repository import (
    StrategyScheduleRunRepository,
)
from finai.infrastructure.database.repositories.strategy_schedule_signal_repository import (
    StrategyScheduleSignalRepository,
)


class StrategyScheduleService:
    def __init__(
        self,
        *,
        session: Session,
        run_service: StrategyRunService,
        maximum_schedules_per_account: int,
    ) -> None:
        self._account_repository = (
            PaperAccountRepository(
                session
            )
        )

        self._schedule_repository = (
            StrategyScheduleRepository(
                session
            )
        )

        self._signal_repository = (
            StrategyScheduleSignalRepository(
                session
            )
        )

        self._schedule_run_repository = (
            StrategyScheduleRunRepository(
                session
            )
        )

        self._run_service = run_service

        self._maximum_schedules_per_account = (
            maximum_schedules_per_account
        )

    def create(
        self,
        *,
        account_id: UUID,
        strategy_key: str,
        name: str,
        frequency: StrategyScheduleFrequency,
        enabled: bool,
        signals: list[dict],
    ):
        normalized_strategy_key = (
            strategy_key.strip()
        )

        normalized_name = name.strip()

        if not normalized_strategy_key:
            raise ValueError(
                "strategy_key cannot be blank."
            )

        if not normalized_name:
            raise ValueError(
                "Schedule name cannot be blank."
            )

        if not signals:
            raise ValueError(
                "Schedule requires at least "
                "one signal."
            )

        account = (
            self._account_repository
            .get_by_id(
                account_id
            )
        )

        if account is None:
            raise LookupError(
                "Paper account not found: "
                f"{account_id}"
            )

        existing = (
            self._schedule_repository
            .list_for_account(
                account_id=account_id
            )
        )

        if (
            len(existing)
            >= self._maximum_schedules_per_account
        ):
            raise ValueError(
                "Maximum schedules per account "
                "has been reached."
            )

        now = datetime.now(UTC)

        next_run_at = calculate_next_run_at(
            frequency=frequency,
            from_time=now,
        )

        schedule = (
            self._schedule_repository.create(
                account_id=account_id,
                strategy_key=(
                    normalized_strategy_key
                ),
                name=normalized_name,
                frequency=frequency.value,
                enabled=enabled,
                next_run_at=next_run_at,
            )
        )

        self._signal_repository.create_many(
            schedule_id=schedule.id,
            signals=signals,
        )

        return schedule

    def get(
        self,
        *,
        schedule_id: UUID,
    ):
        schedule = (
            self._schedule_repository
            .get_by_id(
                schedule_id
            )
        )

        if schedule is None:
            raise LookupError(
                "Strategy schedule not found: "
                f"{schedule_id}"
            )

        return schedule

    def list_signals(
        self,
        *,
        schedule_id: UUID,
    ):
        return (
            self._signal_repository
            .list_for_schedule(
                schedule_id=schedule_id
            )
        )

    def enable(
        self,
        *,
        schedule_id: UUID,
    ):
        schedule = self.get(
            schedule_id=schedule_id
        )

        return (
            self._schedule_repository
            .set_enabled(
                schedule,
                enabled=True,
            )
        )

    def disable(
        self,
        *,
        schedule_id: UUID,
    ):
        schedule = self.get(
            schedule_id=schedule_id
        )

        return (
            self._schedule_repository
            .set_enabled(
                schedule,
                enabled=False,
            )
        )

    def run(
        self,
        *,
        schedule_id: UUID,
        lease_owner: str | None = None,
    ):
        schedule = self.get(
            schedule_id=schedule_id
        )

        if not schedule.enabled:
            raise ValueError(
                "Strategy schedule is disabled."
            )

        now = datetime.now(UTC)

        if (
            self._schedule_repository
            .has_active_lease(
                model=schedule,
                now=now,
                expected_owner=lease_owner,
            )
        ):
            raise ValueError(
                "Strategy schedule is currently "
                "leased by another worker."
            )

        signals = self.list_signals(
            schedule_id=schedule.id
        )

        if not signals:
            raise ValueError(
                "Strategy schedule contains "
                "no signals."
            )

        schedule_run = (
            self._schedule_run_repository
            .create_started(
                schedule_id=schedule.id
            )
        )

        strategy_signals = [
            StrategySignal(
                symbol=signal.symbol,
                side=OrderSide(
                    signal.side
                ),
                confidence=(
                    signal.confidence
                ),
                source_model_id=(
                    signal.source_model_id
                ),
                source_prediction_id=(
                    signal.source_prediction_id
                ),
            )
            for signal in signals
        ]

        try:
            run = self._run_service.execute(
                account_id=(
                    schedule.account_id
                ),
                strategy_key=(
                    schedule.strategy_key
                ),
                idempotency_key=(
                    f"schedule-{schedule.id}-"
                    f"{uuid4().hex}"
                ),
                signals=strategy_signals,
            )

        except Exception as error:  # noqa: BLE001
            (
                self._schedule_run_repository
                .mark_failed(
                    schedule_run,
                    error_message=str(
                        error
                    ),
                )
            )

            raise

        (
            self._schedule_run_repository
            .mark_completed(
                schedule_run,
                strategy_run_id=run.id,
            )
        )

        completed_at = datetime.now(UTC)

        frequency = (
            StrategyScheduleFrequency(
                schedule.frequency
            )
        )

        next_run_at = calculate_next_run_at(
            frequency=frequency,
            from_time=completed_at,
        )

        (
            self._schedule_repository
            .update_after_run(
                schedule,
                completed_at=completed_at,
                next_run_at=next_run_at,
            )
        )

        return run