from __future__ import annotations

import json
from datetime import (
    UTC,
    datetime,
)
from pathlib import Path

import pandas as pd

from finai.application.services.v34_learning_factory import (
    create_v34_learning_service,
)
from finai.core.config import (
    get_settings,
)


def parse_timestamp(
    value: str,
) -> datetime:
    timestamp = (
        datetime.fromisoformat(
            value
        )
    )

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(
            tzinfo=UTC
        )

    return timestamp.astimezone(
        UTC
    )


def main() -> None:
    settings = get_settings()

    decision_path = Path(
        settings.v36_decision_log_path
    )

    outcome_path = Path(
        settings.v36_outcome_log_path
    )

    if not decision_path.exists():
        print(
            "No V3.6 decisions exist yet."
        )

        return

    service = (
        create_v34_learning_service(
            settings=settings
        )
    )

    bars = service.load_market_bars(
        symbol=(
            settings.v36_symbol
        ),
        interval=(
            settings.v36_interval
        ),
    )

    bars = bars.copy()

    bars["timestamp"] = pd.to_datetime(
        bars[
            "timestamp"
        ],
        utc=True,
    )

    existing_ids = set()

    if outcome_path.exists():
        with outcome_path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            for line in handle:
                if not line.strip():
                    continue

                payload = json.loads(
                    line
                )

                existing_ids.add(
                    payload[
                        "decision_id"
                    ]
                )

    written = 0

    with decision_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for line in handle:
            if not line.strip():
                continue

            decision = json.loads(
                line
            )

            decision_id = decision[
                "decision_id"
            ]

            if decision_id in existing_ids:
                continue

            signal = decision[
                "signal"
            ]

            if signal not in {
                "buy",
                "sell",
            }:
                continue

            if not decision[
                "should_execute"
            ]:
                continue

            entry_timestamp = (
                parse_timestamp(
                    decision[
                        "timestamp"
                    ]
                )
            )

            future = bars[
                bars[
                    "timestamp"
                ]
                > pd.Timestamp(
                    entry_timestamp
                )
            ].head(
                settings
                .v36_outcome_horizon_bars
            )

            if (
                len(
                    future
                )
                < (
                    settings
                    .v36_outcome_horizon_bars
                )
            ):
                continue

            outcome_bar = (
                future.iloc[
                    -1
                ]
            )

            entry_price = float(
                decision[
                    "reference_price"
                ]
            )

            outcome_price = float(
                outcome_bar[
                    "close_price"
                ]
            )

            raw_return = (
                outcome_price
                / entry_price
                - 1.0
            )

            if signal == "buy":
                strategy_return = (
                    raw_return
                )

            else:
                strategy_return = (
                    -raw_return
                )

            payload = {
                "decision_id": (
                    decision_id
                ),
                "symbol": (
                    decision[
                        "symbol"
                    ]
                ),
                "side": signal,
                "entry_timestamp": (
                    entry_timestamp
                    .isoformat()
                ),
                "outcome_timestamp": (
                    pd.Timestamp(
                        outcome_bar[
                            "timestamp"
                        ]
                    )
                    .to_pydatetime()
                    .astimezone(UTC)
                    .isoformat()
                ),
                "entry_price": (
                    entry_price
                ),
                "outcome_price": (
                    outcome_price
                ),
                "gross_return": (
                    strategy_return
                ),
                "correct_direction": (
                    strategy_return > 0.0
                ),
            }

            outcome_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with outcome_path.open(
                "a",
                encoding="utf-8",
            ) as output:
                output.write(
                    json.dumps(
                        payload,
                        sort_keys=True,
                    )
                )

                output.write(
                    "\n"
                )

            written += 1

    print(
        "V3.6 outcome attribution complete."
    )

    print(
        "new_outcomes=",
        written,
    )


if __name__ == "__main__":
    main()