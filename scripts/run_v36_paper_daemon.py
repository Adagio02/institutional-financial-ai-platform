from __future__ import annotations

import subprocess
import sys
import time

from finai.core.config import (
    get_settings,
)


def run_script(
    script: str,
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            script,
        ],
        check=False,
    )

    if result.returncode != 0:
        print(
            "V3.6 child process failed: "
            f"{script}, "
            f"code={result.returncode}"
        )


def main() -> None:
    settings = get_settings()

    if not settings.v36_execution_enabled:
        raise RuntimeError(
            "V3.6 execution is disabled."
        )

    if settings.v36_live_money_enabled:
        raise RuntimeError(
            "V3.6 refuses live-money mode."
        )

    print(
        "V3.6 continuous paper daemon started."
    )

    while True:
        run_script(
            "scripts/"
            "run_v36_paper_cycle.py"
        )

        run_script(
            "scripts/"
            "attribute_v36_outcomes.py"
        )

        time.sleep(
            settings
            .v36_cycle_interval_seconds
        )


if __name__ == "__main__":
    main()