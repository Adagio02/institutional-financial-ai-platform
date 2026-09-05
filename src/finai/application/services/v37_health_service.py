from __future__ import annotations

import json
from dataclasses import asdict
from datetime import (
    UTC,
    datetime,
)
from pathlib import Path

import pandas as pd

from finai.application.services.v34_learning_factory import (
    create_v34_learning_service,
)
from finai.core.config import Settings
from finai.domain.learning.v37_runtime import (
    V37PlatformHealth,
)


class V37HealthService:
    def __init__(
        self,
        *,
        settings: Settings,
    ) -> None:
        self._settings = settings

        self._health_path = Path(
            settings.v37_health_path
        )

        self._kill_switch_path = Path(
            settings.v37_kill_switch_path
        )

        self._champion_path = (
            Path(
                settings
                .v36_champion_directory
            )
            / "champion.joblib"
        )

        self._learning_service = (
            create_v34_learning_service(
                settings=settings
            )
        )

    def check(
        self,
    ) -> V37PlatformHealth:
        now = datetime.now(
            UTC
        )

        kill_switch_active = (
            self
            ._kill_switch_path
            .exists()
        )

        champion_exists = (
            self._champion_path.exists()
        )

        latest_timestamp = None
        market_age = None
        total_market_bars = 0

        market_status = (
            "unavailable"
        )

        message = (
            "No market data is available."
        )

        try:
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

            total_market_bars = len(
                bars
            )

            if total_market_bars > 0:
                latest = pd.Timestamp(
                    bars.iloc[
                        -1
                    ][
                        "timestamp"
                    ]
                )

                latest_timestamp = (
                    latest
                    .to_pydatetime()
                )

                if (
                    latest_timestamp
                    .tzinfo
                    is None
                ):
                    latest_timestamp = (
                        latest_timestamp
                        .replace(
                            tzinfo=UTC
                        )
                    )

                latest_timestamp = (
                    latest_timestamp
                    .astimezone(UTC)
                )

                market_age = (
                    now
                    - latest_timestamp
                ).total_seconds()

                if (
                    market_age
                    <= (
                        self
                        ._settings
                        .v37_market_data_warning_age_seconds
                    )
                ):
                    market_status = "fresh"

                    message = (
                        "Market data is fresh."
                    )

                elif (
                    market_age
                    <= (
                        self
                        ._settings
                        .v37_market_data_failure_age_seconds
                    )
                ):
                    market_status = "warning"

                    message = (
                        "Market data is aging."
                    )

                else:
                    market_status = "stale"

                    message = (
                        "Market data is stale."
                    )

        except Exception as error:
            message = (
                "Health check could not load "
                "market data: "
                f"{error!r}"
            )

        paper_safe = (
            self._settings.execution_mode
            == "alpaca_paper"
            and not (
                self
                ._settings
                .v36_live_money_enabled
            )
            and not (
                self
                ._settings
                .v37_live_money_enabled
            )
        )

        healthy = (
            paper_safe
            and not kill_switch_active
            and market_status
            in {
                "fresh",
                "warning",
            }
        )

        health = V37PlatformHealth(
            timestamp=now,
            healthy=healthy,
            execution_mode=(
                self
                ._settings
                .execution_mode
            ),
            live_money_enabled=(
                self
                ._settings
                .v37_live_money_enabled
            ),
            kill_switch_active=(
                kill_switch_active
            ),
            latest_market_timestamp=(
                latest_timestamp
            ),
            market_data_age_seconds=(
                market_age
            ),
            market_data_status=(
                market_status
            ),
            champion_exists=(
                champion_exists
            ),
            total_market_bars=(
                total_market_bars
            ),
            message=message,
        )

        self._write_health(
            health
        )

        return health

    def _write_health(
        self,
        health: V37PlatformHealth,
    ) -> None:
        payload = asdict(
            health
        )

        for key in (
            "timestamp",
            "latest_market_timestamp",
        ):
            value = payload.get(
                key
            )

            if value is not None:
                payload[
                    key
                ] = (
                    value.isoformat()
                )

        self._health_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = (
            self._health_path
            .with_suffix(
                ".tmp"
            )
        )

        temporary.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        temporary.replace(
            self._health_path
        )