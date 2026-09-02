from __future__ import annotations

import subprocess
import sys
import time
from datetime import (
    UTC,
    datetime,
)


LEARNING_INTERVAL_SECONDS = (
    60 * 60
)

MAXIMUM_BACKOFF_SECONDS = (
    60 * 60 * 4
)


def run_learning_cycle() -> bool:
    print()
    print(
        "=" * 70
    )

    print(
        "ADAPTIVE LEARNING CYCLE"
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
            "scripts/run_v34_learning_cycle.py",
        ],
        check=False,
    )

    return (
        result.returncode
        == 0
    )


def main() -> None:
    print(
        "Starting adaptive-learning daemon."
    )

    print(
        "Training interval: "
        f"{LEARNING_INTERVAL_SECONDS} "
        "seconds"
    )

    failure_count = 0

    try:
        while True:
            success = (
                run_learning_cycle()
            )

            if success:
                failure_count = 0

                sleep_seconds = (
                    LEARNING_INTERVAL_SECONDS
                )

            else:
                failure_count += 1

                sleep_seconds = min(
                    LEARNING_INTERVAL_SECONDS
                    * (
                        2
                        ** min(
                            failure_count,
                            2,
                        )
                    ),
                    MAXIMUM_BACKOFF_SECONDS,
                )

                print(
                    "Learning cycle failed. "
                    "Retrying in "
                    f"{sleep_seconds} seconds."
                )

            time.sleep(
                sleep_seconds
            )

    except KeyboardInterrupt:
        print()
        print(
            "Learning daemon stopped."
        )


if __name__ == "__main__":
    main()