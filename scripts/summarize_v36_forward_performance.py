from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from finai.core.config import (
    get_settings,
)


def main() -> None:
    settings = get_settings()

    path = Path(
        settings.v36_outcome_log_path
    )

    if not path.exists():
        print(
            "No V3.6 outcomes exist yet."
        )

        return

    outcomes = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for line in handle:
            if line.strip():
                outcomes.append(
                    json.loads(
                        line
                    )
                )

    if not outcomes:
        print(
            "No V3.6 outcomes exist yet."
        )

        return

    returns = np.asarray(
        [
            float(
                outcome[
                    "gross_return"
                ]
            )
            for outcome
            in outcomes
        ],
        dtype=float,
    )

    wins = int(
        np.sum(
            returns > 0.0
        )
    )

    losses = int(
        np.sum(
            returns <= 0.0
        )
    )

    win_rate = (
        wins
        / len(
            returns
        )
    )

    compounded_return = float(
        np.prod(
            1.0
            + returns
        )
        - 1.0
    )

    average_return = float(
        np.mean(
            returns
        )
    )

    median_return = float(
        np.median(
            returns
        )
    )

    print(
        "=== V3.6 FORWARD PAPER PERFORMANCE ==="
    )

    print(
        "observations =",
        len(
            returns
        ),
    )

    print(
        "wins =",
        wins,
    )

    print(
        "losses =",
        losses,
    )

    print(
        "win_rate =",
        win_rate,
    )

    print(
        "average_return =",
        average_return,
    )

    print(
        "median_return =",
        median_return,
    )

    print(
        "compounded_return =",
        compounded_return,
    )


if __name__ == "__main__":
    main()