from __future__ import annotations

import subprocess
import sys
import time
from datetime import (
    UTC,
    datetime,
)
from pathlib import Path

from finai.application.services.v34_learning_factory import (
    create_v34_learning_service,
)
from finai.application.services.v37_health_service import (
    V37HealthService,
)
from finai.application.services.v37_runtime_state_service import (
    V37RuntimeStateService,
)
from finai.core.config import (
    get_settings,
)


def utc_now() -> datetime:
    return datetime.now(
        UTC
    )


class V37AutonomousPlatform:
    def __init__(
        self,
    ) -> None:
        self._settings = (
            get_settings()
        )

        if not (
            self
            ._settings
            .v37_autonomous_enabled
        ):
            raise RuntimeError(
                "V3.7 autonomous operation "
                "is disabled."
            )

        if (
            self
            ._settings
            .v37_live_money_enabled
        ):
            raise RuntimeError(
                "V3.7 refuses live-money mode."
            )

        if (
            self
            ._settings
            .v36_live_money_enabled
        ):
            raise RuntimeError(
                "V3.6 live-money mode must "
                "remain disabled."
            )

        if (
            self
            ._settings
            .execution_mode
            != "alpaca_paper"
        ):
            raise RuntimeError(
                "V3.7 requires "
                "EXECUTION_MODE=alpaca_paper."
            )

        self._state_service = (
            V37RuntimeStateService(
                state_path=(
                    self
                    ._settings
                    .v37_state_path
                ),
                event_log_path=(
                    self
                    ._settings
                    .v37_event_log_path
                ),
            )
        )

        self._health_service = (
            V37HealthService(
                settings=(
                    self._settings
                )
            )
        )

        self._learning_service = (
            create_v34_learning_service(
                settings=(
                    self._settings
                )
            )
        )

        self._kill_switch = Path(
            self
            ._settings
            .v37_kill_switch_path
        )

        self._state = (
            self
            ._state_service
            .load()
        )

        self._next_ingestion = 0.0
        self._next_execution = 0.0
        self._next_attribution = 0.0
        self._next_health = 0.0

        self._next_learning_check = 0.0

        self._job_failures: dict[
            str,
            int,
        ] = {}

    def _record_job_start(
        self,
        *,
        name: str,
    ) -> None:
        jobs = self._state.setdefault(
            "jobs",
            {},
        )

        job = jobs.setdefault(
            name,
            {},
        )

        job[
            "last_started_at"
        ] = (
            self
            ._state_service
            .utc_now_string()
        )

        self._state_service.save(
            self._state
        )

    def _record_job_result(
        self,
        *,
        name: str,
        success: bool,
        error: str | None,
    ) -> None:
        jobs = self._state.setdefault(
            "jobs",
            {},
        )

        job = jobs.setdefault(
            name,
            {},
        )

        job[
            "last_completed_at"
        ] = (
            self
            ._state_service
            .utc_now_string()
        )

        job[
            "last_success"
        ] = success

        job[
            "last_error"
        ] = error

        if success:
            self._job_failures[
                name
            ] = 0

            job[
                "consecutive_failures"
            ] = 0

        else:
            failures = (
                self
                ._job_failures
                .get(
                    name,
                    0,
                )
                + 1
            )

            self._job_failures[
                name
            ] = failures

            job[
                "consecutive_failures"
            ] = failures

        self._state_service.save(
            self._state
        )

    def _run_python(
        self,
        *,
        name: str,
        arguments: list[str],
        timeout_seconds: int,
    ) -> bool:
        self._record_job_start(
            name=name
        )

        command = [
            sys.executable,
            *arguments,
        ]

        print()
        print(
            "=" * 72
        )

        print(
            f"V3.7 JOB: {name}"
        )

        print(
            "time=",
            utc_now()
            .isoformat(),
        )

        print(
            "command=",
            " ".join(
                command
            ),
        )

        try:
            result = subprocess.run(
                command,
                check=False,
                timeout=(
                    timeout_seconds
                ),
            )

        except subprocess.TimeoutExpired as error:
            message = (
                f"Job timed out: {error}"
            )

            print(
                message
            )

            self._record_job_result(
                name=name,
                success=False,
                error=message,
            )

            self._state_service.record_event(
                event_type=(
                    "job_timeout"
                ),
                message=message,
                details={
                    "job": name,
                },
            )

            return False

        success = (
            result.returncode
            == 0
        )

        if success:
            self._record_job_result(
                name=name,
                success=True,
                error=None,
            )

            return True

        message = (
            f"Job failed with exit code "
            f"{result.returncode}."
        )

        print(
            message
        )

        self._record_job_result(
            name=name,
            success=False,
            error=message,
        )

        self._state_service.record_event(
            event_type="job_failure",
            message=message,
            details={
                "job": name,
                "returncode": (
                    result.returncode
                ),
            },
        )

        return False

    def _backoff_seconds(
        self,
        *,
        name: str,
    ) -> int:
        failures = (
            self
            ._job_failures
            .get(
                name,
                0,
            )
        )

        if failures <= 0:
            return 0

        seconds = (
            self
            ._settings
            .v37_initial_backoff_seconds
            * (
                2
                ** min(
                    failures - 1,
                    5,
                )
            )
        )

        return min(
            seconds,
            self
            ._settings
            .v37_maximum_backoff_seconds,
        )

    def _ingest(
        self,
    ) -> bool:
        return self._run_python(
            name="market_ingestion",
            arguments=[
                (
                    self
                    ._settings
                    .v37_ingestion_script
                ),
                "--symbol",
                (
                    self
                    ._settings
                    .v37_symbol
                ),
                "--interval",
                (
                    self
                    ._settings
                    .v37_interval
                ),
                "--days",
                str(
                    self
                    ._settings
                    .v37_ingestion_lookback_days
                ),
            ],
            timeout_seconds=300,
        )

    def _execute(
        self,
    ) -> bool:
        return self._run_python(
            name="paper_execution",
            arguments=[
                (
                    self
                    ._settings
                    .v37_execution_script
                ),
            ],
            timeout_seconds=120,
        )

    def _attribute(
        self,
    ) -> bool:
        return self._run_python(
            name="outcome_attribution",
            arguments=[
                (
                    self
                    ._settings
                    .v37_attribution_script
                ),
            ],
            timeout_seconds=120,
        )

    def _market_bar_count(
        self,
    ) -> int:
        bars = (
            self
            ._learning_service
            .load_market_bars(
                symbol=(
                    self
                    ._settings
                    .v37_symbol
                ),
                interval=(
                    self
                    ._settings
                    .v37_interval
                ),
            )
        )

        return len(
            bars
        )

    def _learning_due(
        self,
    ) -> tuple[
        bool,
        int,
        int,
    ]:
        current_rows = (
            self._market_bar_count()
        )

        previous_rows = int(
            self._state.get(
                "last_learning_bar_count",
                0,
            )
        )

        new_rows = max(
            0,
            current_rows
            - previous_rows,
        )

        last_raw = self._state.get(
            "last_learning_timestamp"
        )

        if last_raw is None:
            time_due = True

        else:
            last_timestamp = (
                datetime
                .fromisoformat(
                    str(
                        last_raw
                    )
                )
            )

            if (
                last_timestamp
                .tzinfo
                is None
            ):
                last_timestamp = (
                    last_timestamp
                    .replace(
                        tzinfo=UTC
                    )
                )

            elapsed = (
                utc_now()
                - last_timestamp
                .astimezone(UTC)
            ).total_seconds()

            time_due = (
                elapsed
                >= (
                    self
                    ._settings
                    .v37_learning_interval_seconds
                )
            )

        enough_new_data = (
            new_rows
            >= (
                self
                ._settings
                .v37_learning_minimum_new_bars
            )
        )

        return (
            time_due
            and enough_new_data,
            current_rows,
            new_rows,
        )

    def _learn_if_due(
        self,
    ) -> None:
        try:
            (
                due,
                current_rows,
                new_rows,
            ) = self._learning_due()

        except Exception as error:
            print(
                "Could not evaluate learning "
                "schedule:",
                repr(
                    error
                ),
            )

            return

        print(
            "Learning status: "
            f"rows={current_rows}, "
            f"new_rows={new_rows}, "
            f"due={due}"
        )

        if not due:
            return

        success = self._run_python(
            name="adaptive_learning",
            arguments=[
                (
                    self
                    ._settings
                    .v37_learning_script
                ),
            ],
            timeout_seconds=3600,
        )

        if not success:
            return

        self._state[
            "last_learning_bar_count"
        ] = current_rows

        self._state[
            "last_learning_timestamp"
        ] = (
            utc_now()
            .isoformat()
        )

        self._state_service.save(
            self._state
        )

        self._state_service.record_event(
            event_type=(
                "learning_completed"
            ),
            message=(
                "Adaptive learning cycle "
                "completed."
            ),
            details={
                "market_bar_count": (
                    current_rows
                ),
                "new_rows": new_rows,
            },
        )

    def _check_health(
        self,
    ) -> None:
        health = (
            self
            ._health_service
            .check()
        )

        print()
        print(
            "=== V3.7 HEALTH ==="
        )

        print(
            "healthy =",
            health.healthy,
        )

        print(
            "market_data =",
            health.market_data_status,
        )

        print(
            "market_age_seconds =",
            health.market_data_age_seconds,
        )

        print(
            "champion_exists =",
            health.champion_exists,
        )

        print(
            "kill_switch =",
            health.kill_switch_active,
        )

    def run(
        self,
    ) -> None:
        self._state_service.record_event(
            event_type=(
                "platform_started"
            ),
            message=(
                "V3.7 autonomous platform started."
            ),
        )

        print()
        print(
            "=" * 72
        )

        print(
            "FINAI V3.7 AUTONOMOUS "
            "PAPER PLATFORM"
        )

        print(
            "=" * 72
        )

        print(
            "execution_mode =",
            self
            ._settings
            .execution_mode,
        )

        print(
            "live_money =",
            self
            ._settings
            .v37_live_money_enabled,
        )

        print(
            "kill_switch =",
            self._kill_switch,
        )

        print()

        try:
            while True:
                if (
                    self
                    ._kill_switch
                    .exists()
                ):
                    print()
                    print(
                        "V3.7 kill switch is active."
                    )

                    print(
                        "Autonomous operations "
                        "are paused."
                    )

                    self._check_health()

                    time.sleep(
                        5
                    )

                    continue

                now = time.monotonic()

                if (
                    now
                    >= self
                    ._next_ingestion
                ):
                    success = self._ingest()

                    delay = (
                        self
                        ._backoff_seconds(
                            name=(
                                "market_ingestion"
                            )
                        )
                    )

                    self._next_ingestion = (
                        time.monotonic()
                        + (
                            delay
                            if not success
                            else (
                                self
                                ._settings
                                .v37_ingestion_interval_seconds
                            )
                        )
                    )

                now = time.monotonic()

                if (
                    now
                    >= self
                    ._next_execution
                ):
                    success = self._execute()

                    delay = (
                        self
                        ._backoff_seconds(
                            name=(
                                "paper_execution"
                            )
                        )
                    )

                    self._next_execution = (
                        time.monotonic()
                        + (
                            delay
                            if not success
                            else (
                                self
                                ._settings
                                .v37_execution_interval_seconds
                            )
                        )
                    )

                now = time.monotonic()

                if (
                    now
                    >= self
                    ._next_attribution
                ):
                    success = (
                        self._attribute()
                    )

                    delay = (
                        self
                        ._backoff_seconds(
                            name=(
                                "outcome_attribution"
                            )
                        )
                    )

                    self._next_attribution = (
                        time.monotonic()
                        + (
                            delay
                            if not success
                            else (
                                self
                                ._settings
                                .v37_attribution_interval_seconds
                            )
                        )
                    )

                now = time.monotonic()

                if (
                    now
                    >= self
                    ._next_learning_check
                ):
                    self._learn_if_due()

                    self._next_learning_check = (
                        time.monotonic()
                        + 300
                    )

                now = time.monotonic()

                if (
                    now
                    >= self
                    ._next_health
                ):
                    self._check_health()

                    self._next_health = (
                        time.monotonic()
                        + (
                            self
                            ._settings
                            .v37_health_interval_seconds
                        )
                    )

                time.sleep(
                    1
                )

        except KeyboardInterrupt:
            print()
            print(
                "V3.7 autonomous platform "
                "stopped by operator."
            )

            self._state_service.record_event(
                event_type=(
                    "platform_stopped"
                ),
                message=(
                    "V3.7 platform stopped "
                    "by operator."
                ),
            )


def main() -> None:
    platform = (
        V37AutonomousPlatform()
    )

    platform.run()


if __name__ == "__main__":
    main()