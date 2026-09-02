from __future__ import annotations

import subprocess
import sys
import time
from datetime import (
    UTC,
    datetime,
)


CYCLE_SECONDS = 60

MAXIMUM_BACKOFF_SECONDS = 300


def run_cycle() -> bool:
    print()
    print(
        "=" * 70
    )

    print(
        "V3.6 PAPER EXECUTION CYCLE"
    )

    print(
        "time=",
        datetime.now(
            UTC
        ).isoformat(),
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_v36_paper_cycle.py",
        ],
        check=False,
    )

    return (
        result.returncode
        == 0
    )


def main() -> None:
    print(
        "Starting V3.6 paper "
        "execution daemon."
    )

    print(
        f"Cycle interval: "
        f"{CYCLE_SECONDS} seconds"
    )

    failure_count = 0

    try:
        while True:
            success = (
                run_cycle()
            )

            if success:
                failure_count = 0

                sleep_seconds = (
                    CYCLE_SECONDS
                )

            else:
                failure_count += 1

                sleep_seconds = min(
                    CYCLE_SECONDS
                    * (
                        2
                        ** min(
                            failure_count,
                            3,
                        )
                    ),
                    MAXIMUM_BACKOFF_SECONDS,
                )

                print(
                    "Execution cycle failed. "
                    "Retrying in "
                    f"{sleep_seconds} seconds."
                )

            time.sleep(
                sleep_seconds
            )

    except KeyboardInterrupt:
        print()
        print(
            "V3.6 execution daemon stopped."
        )


if __name__ == "__main__":
    main()