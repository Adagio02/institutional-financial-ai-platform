from __future__ import annotations

import subprocess
import sys
import time
from datetime import (
    UTC,
    datetime,
)


SYMBOL = "AAPL"
INTERVAL = "1m"

INGEST_DAYS = 1

POLL_SECONDS = 30

MAXIMUM_BACKOFF_SECONDS = 300


def run_ingestion() -> bool:
    command = [
        sys.executable,
        "scripts/ingest_alpaca_history_v30.py",
        "--symbol",
        SYMBOL,
        "--interval",
        INTERVAL,
        "--days",
        str(
            INGEST_DAYS
        ),
    ]

    print()
    print(
        "=" * 70
    )

    print(
        "V3.6 MARKET DATA REFRESH"
    )

    print(
        "time=",
        datetime.now(
            UTC
        ).isoformat(),
    )

    print(
        "symbol=",
        SYMBOL,
    )

    print(
        "interval=",
        INTERVAL,
    )

    result = subprocess.run(
        command,
        check=False,
    )

    if result.returncode != 0:
        print(
            "Market-data ingestion failed. "
            f"exit_code={result.returncode}"
        )

        return False

    print(
        "Market-data refresh completed."
    )

    return True


def main() -> None:
    print(
        "Starting V3.6 Alpaca "
        "market-data daemon."
    )

    print(
        f"Poll interval: "
        f"{POLL_SECONDS} seconds"
    )

    failure_count = 0

    try:
        while True:
            success = (
                run_ingestion()
            )

            if success:
                failure_count = 0

                sleep_seconds = (
                    POLL_SECONDS
                )

            else:
                failure_count += 1

                sleep_seconds = min(
                    POLL_SECONDS
                    * (
                        2
                        ** min(
                            failure_count,
                            4,
                        )
                    ),
                    MAXIMUM_BACKOFF_SECONDS,
                )

                print(
                    "Retrying ingestion in "
                    f"{sleep_seconds} seconds."
                )

            time.sleep(
                sleep_seconds
            )

    except KeyboardInterrupt:
        print()
        print(
            "Market-data daemon stopped."
        )


if __name__ == "__main__":
    main()