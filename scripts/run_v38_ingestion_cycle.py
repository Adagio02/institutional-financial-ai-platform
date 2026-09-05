from __future__ import annotations

import subprocess
import sys


SYMBOLS = [
    "AAPL",
    "SPY",
    "QQQ",
]


def main() -> None:
    for symbol in SYMBOLS:
        print()
        print(
            "=" * 60
        )

        print(
            "V3.8 ingestion:",
            symbol,
        )

        result = subprocess.run(
            [
                sys.executable,
                (
                    "scripts/"
                    "ingest_alpaca_history_v30.py"
                ),
                "--symbol",
                symbol,
                "--interval",
                "1m",
                "--days",
                "2",
            ],
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "V3.8 ingestion failed. "
                f"symbol={symbol}, "
                f"exit_code="
                f"{result.returncode}"
            )


if __name__ == "__main__":
    main()