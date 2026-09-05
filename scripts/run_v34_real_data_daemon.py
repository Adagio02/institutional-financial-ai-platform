from __future__ import annotations

import json
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
from finai.core.config import (
    get_settings,
)


def utc_now() -> datetime:
    return datetime.now(
        UTC
    )


def run_ingestion(
    *,
    symbol: str,
    interval: str,
    days: int,
) -> None:
    command = [
        sys.executable,
        "scripts/ingest_alpaca_history_v30.py",
        "--symbol",
        symbol,
        "--interval",
        interval,
        "--days",
        str(days),
    ]

    subprocess.run(
        command,
        check=True,
    )


def main() -> None:
    settings = get_settings()

    service = (
        create_v34_learning_service(
            settings=settings
        )
    )

    artifact_directory = Path(
        settings
        .v34_learning_artifact_directory
    )

    artifact_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    state_path = (
        artifact_directory
        / "daemon_state.json"
    )

    previous_rows = 0

    last_learning_timestamp = 0.0

    if state_path.exists():
        state = json.loads(
            state_path.read_text(
                encoding="utf-8"
            )
        )

        previous_rows = int(
            state.get(
                "rows",
                0,
            )
        )

        last_learning_timestamp = float(
            state.get(
                "last_learning_timestamp",
                0.0,
            )
        )

    print(
        "V3.4 real-data daemon started."
    )

    while True:
        try:
            run_ingestion(
                symbol=(
                    settings
                    .v34_learning_symbol
                ),
                interval=(
                    settings
                    .v34_learning_interval
                ),
                days=(
                    settings
                    .v34_ingestion_lookback_days
                ),
            )

            bars = service.load_market_bars(
                symbol=(
                    settings
                    .v34_learning_symbol
                ),
                interval=(
                    settings
                    .v34_learning_interval
                ),
            )

            current_rows = len(
                bars
            )

            new_rows = max(
                0,
                current_rows
                - previous_rows,
            )

            now = time.time()

            enough_time = (
                now
                - last_learning_timestamp
                >= (
                    settings
                    .v34_learning_refresh_seconds
                )
            )

            enough_data = (
                new_rows
                >= (
                    settings
                    .v34_learning_minimum_new_bars
                )
            )

            print(
                "V3.4 real-data status: "
                f"rows={current_rows}, "
                f"new_rows={new_rows}"
            )

            if (
                enough_time
                and enough_data
            ):
                result = (
                    service
                    .run_learning_cycle(
                        symbol=(
                            settings
                            .v34_learning_symbol
                        ),
                        interval=(
                            settings
                            .v34_learning_interval
                        ),
                    )
                )

                print(
                    "V3.4 learning cycle: "
                    f"promoted={result.promoted}, "
                    f"reason="
                    f"{result.promotion_reason}"
                )

                last_learning_timestamp = (
                    now
                )

                previous_rows = (
                    current_rows
                )

            state = {
                "rows": current_rows,
                "last_learning_timestamp": (
                    last_learning_timestamp
                ),
                "updated_at": (
                    utc_now()
                    .isoformat()
                ),
            }

            state_path.write_text(
                json.dumps(
                    state,
                    indent=2,
                ),
                encoding="utf-8",
            )

        except Exception as error:
            print(
                "V3.4 daemon cycle failed:",
                repr(
                    error
                ),
            )

        time.sleep(
            settings
            .v34_ingestion_refresh_seconds
        )


if __name__ == "__main__":
    main()