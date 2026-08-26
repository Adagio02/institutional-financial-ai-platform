from __future__ import annotations

import json
from dataclasses import asdict

import pandas as pd

from finai.application.services.v34_learning_factory import (
    create_v34_learning_service,
)
from finai.application.services.v36_execution_factory import (
    create_v36_execution_service,
)
from finai.core.config import get_settings
from finai.domain.learning.v33_features import (
    FEATURE_COLUMNS,
)


def serialize_dataclass(
    value: object,
) -> str:
    payload = {}

    for key, item in asdict(
        value
    ).items():
        if hasattr(
            item,
            "isoformat",
        ):
            payload[key] = (
                item.isoformat()
            )

        else:
            payload[key] = item

    return json.dumps(
        payload,
        indent=2,
    )


def main() -> None:
    settings = get_settings()

    if not settings.v36_execution_enabled:
        print(
            "V3.6 execution is disabled."
        )

        return

    if settings.v36_live_money_enabled:
        raise RuntimeError(
            "V3.6 refuses live-money execution."
        )

    learning_service = (
        create_v34_learning_service(
            settings=settings
        )
    )

    execution_service = (
        create_v36_execution_service(
            settings=settings
        )
    )

    raw = (
        learning_service
        .load_market_bars(
            symbol=(
                settings.v36_symbol
            ),
            interval=(
                settings.v36_interval
            ),
        )
    )

    if raw.empty:
        raise RuntimeError(
            "No V3.6 market data is available."
        )

    dataset = (
        learning_service
        .build_dataset(
            raw,
            include_target=False,
        )
    )

    if dataset.empty:
        raise RuntimeError(
            "No V3.6 feature rows are available."
        )

    latest = dataset.iloc[
        -1
    ]

    latest_timestamp = pd.Timestamp(
        latest[
            "timestamp"
        ]
    )

    latest_features = dataset.iloc[
        [
            -1,
        ]
    ][
        FEATURE_COLUMNS
    ]

    raw_timestamps = pd.to_datetime(
        raw[
            "timestamp"
        ],
        utc=True,
    )

    matching_raw = raw.loc[
        raw_timestamps
        == latest_timestamp
    ]

    if matching_raw.empty:
        raise RuntimeError(
            "Could not match the latest V3.6 "
            "feature row to its source market bar. "
            f"feature_timestamp={latest_timestamp}"
        )

    source_bar = matching_raw.iloc[
        -1
    ]

    reference_price = float(
        source_bar[
            "close_price"
        ]
    )

    provider = str(
        source_bar[
            "provider"
        ]
    )

    print()
    print(
        "=== V3.6 MARKET INPUT ==="
    )

    print(
        "feature_timestamp =",
        latest_timestamp,
    )

    print(
        "reference_price =",
        reference_price,
    )

    print(
        "provider =",
        provider,
    )

    try:
        decision = (
            execution_service
            .decide(
                symbol=(
                    settings.v36_symbol
                ),
                interval=(
                    settings.v36_interval
                ),
                latest_feature_row=(
                    latest_features
                ),
                latest_timestamp=(
                    latest_timestamp
                ),
                reference_price=(
                    reference_price
                ),
                provider=provider,
            )
        )

    except FileNotFoundError as error:
        print()
        print(
            "V3.6 cycle blocked safely:"
        )

        print(
            str(
                error
            )
        )

        print()
        print(
            "No qualified champion exists yet. "
            "No paper order was submitted."
        )

        return

    except RuntimeError as error:
        print()
        print(
            "V3.6 cycle blocked safely:"
        )

        print(
            str(
                error
            )
        )

        print()
        print(
            "No paper order was submitted."
        )

        return

    print()
    print(
        "=== V3.6 EXECUTION DECISION ==="
    )

    print(
        serialize_dataclass(
            decision
        )
    )

    if not decision.should_execute:
        print()
        print(
            "V3.6 cycle completed "
            "without an order."
        )

        print(
            "Reason:",
            decision.reason,
        )

        return

    try:
        result = (
            execution_service
            .submit(
                decision=decision
            )
        )

    except ValueError as error:
        print()
        print(
            "V3.6 order submission "
            "was blocked:"
        )

        print(
            str(
                error
            )
        )

        return

    print()
    print(
        "=== V3.6 PAPER EXECUTION RESULT ==="
    )

    print(
        serialize_dataclass(
            result
        )
    )

    if result.accepted:
        print()
        print(
            "V3.6 paper order "
            "was accepted."
        )

    else:
        print()
        print(
            "V3.6 paper order "
            "was not accepted."
        )

        if result.error:
            print(
                "Reason:",
                result.error,
            )


if __name__ == "__main__":
    main()