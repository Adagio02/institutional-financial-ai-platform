from __future__ import annotations

import json
from datetime import (
    UTC,
    datetime,
    timedelta,
)
from pathlib import Path
from urllib.error import (
    HTTPError,
    URLError,
)
from urllib.request import (
    Request,
    urlopen,
)
from uuid import uuid4

import joblib
import pandas as pd

from finai.application.services.v38_learning_service import (
    V38LearningService,
)
from finai.application.services.v39_learning_factory import (
    create_v39_learning_service,
)
from finai.core.config import (
    get_settings,
)
from finai.domain.learning.v38_features import (
    V38_FEATURE_COLUMNS,
)


def append_jsonl(
    *,
    path: Path,
    payload: dict[str, object],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            json.dumps(
                payload,
                sort_keys=True,
            )
        )

        handle.write(
            "\n"
        )


def main() -> None:
    settings = get_settings()

    if not settings.v39_execution_enabled:
        print(
            "V3.9 execution is disabled."
        )

        return

    if settings.v39_live_money_enabled:
        raise RuntimeError(
            "V3.9 refuses live-money execution."
        )

    if settings.execution_mode != "alpaca_paper":
        raise RuntimeError(
            "V3.9 requires alpaca_paper mode."
        )

    service = (
        create_v39_learning_service(
            settings=settings
        )
    )

    artifact_directory = Path(
        settings
        .v39_learning_artifact_directory
    )

    champion_path = (
        artifact_directory
        / "champion.joblib"
    )

    metadata_path = (
        artifact_directory
        / "champion.json"
    )

    if not champion_path.exists():
        print()
        print(
            "V3.9 cycle blocked safely:"
        )

        print(
            "No qualified V3.9 champion exists."
        )

        print()
        print(
            "No paper order was submitted."
        )

        return

    if not metadata_path.exists():
        print()
        print(
            "V3.9 cycle blocked safely:"
        )

        print(
            "Champion metadata does not exist."
        )

        print()
        print(
            "No paper order was submitted."
        )

        return

    dataset, _ = (
        service.build_dataset(
            symbol=(
                settings
                .v39_learning_symbol
            ),
            interval=(
                settings
                .v39_learning_interval
            ),
            include_target=False,
        )
    )

    if dataset.empty:
        raise RuntimeError(
            "No live V3.9 feature row exists."
        )

    latest = dataset.iloc[
        -1
    ]

    timestamp = pd.Timestamp(
        latest[
            "timestamp"
        ]
    ).to_pydatetime()

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(
            tzinfo=UTC
        )

    timestamp = timestamp.astimezone(
        UTC
    )

    age = (
        datetime.now(UTC)
        - timestamp
    )

    print()
    print(
        "=== V3.9 MARKET INPUT ==="
    )

    print(
        "feature_timestamp =",
        timestamp,
    )

    print(
        "market_data_age_seconds =",
        age.total_seconds(),
    )

    print(
        "symbol =",
        settings.v39_learning_symbol,
    )

    if age > timedelta(
        seconds=(
            settings
            .v39_maximum_market_data_age_seconds
        )
    ):
        decision_id = (
            "v39-"
            + uuid4().hex
        )

        decision = {
            "decision_id": (
                decision_id
            ),
            "timestamp": (
                timestamp.isoformat()
            ),
            "symbol": (
                settings
                .v39_learning_symbol
            ),
            "interval": (
                settings
                .v39_learning_interval
            ),
            "signal": "hold",
            "should_execute": False,
            "reason": (
                "Market data is stale."
            ),
            "market_data_age_seconds": (
                age.total_seconds()
            ),
        }

        append_jsonl(
            path=Path(
                settings
                .v39_decision_log_path
            ),
            payload=decision,
        )

        print()
        print(
            json.dumps(
                decision,
                indent=2,
            )
        )

        print()
        print(
            "V3.9 cycle completed "
            "without an order."
        )

        return

    metadata = json.loads(
        metadata_path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        metadata,
        dict,
    ):
        raise RuntimeError(
            "V3.9 champion metadata "
            "is invalid."
        )

    version = str(
        metadata.get(
            "version",
            "",
        )
    )

    if version != "3.9":
        raise RuntimeError(
            "Champion is not "
            "V3.9-compatible. "
            f"version={version!r}"
        )

    metadata_features = metadata.get(
        "feature_columns"
    )

    if (
        metadata_features
        != V38_FEATURE_COLUMNS
    ):
        raise RuntimeError(
            "V3.9 champion feature schema "
            "does not match the runtime "
            "feature schema."
        )

    try:
        long_threshold = float(
            metadata[
                "long_threshold"
            ]
        )

        short_threshold = float(
            metadata[
                "short_threshold"
            ]
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        raise RuntimeError(
            "V3.9 champion thresholds "
            "are invalid."
        ) from error

    model = joblib.load(
        champion_path
    )

    features = dataset.iloc[
        [-1]
    ][
        V38_FEATURE_COLUMNS
    ]

    probabilities = model.predict_proba(
        features
    )

    positions = (
        V38LearningService
        .positions_from_probabilities(
            probabilities=probabilities,
            classes=model.classes_,
            long_threshold=(
                long_threshold
            ),
            short_threshold=(
                short_threshold
            ),
        )
    )

    position = int(
        positions[
            0
        ]
    )

    probability_by_class = {
        int(label): float(
            probability
        )
        for label, probability
        in zip(
            model.classes_,
            probabilities[
                0
            ],
            strict=True,
        )
    }

    buy_probability = (
        probability_by_class
        .get(
            1,
            0.0,
        )
    )

    hold_probability = (
        probability_by_class
        .get(
            0,
            0.0,
        )
    )

    sell_probability = (
        probability_by_class
        .get(
            -1,
            0.0,
        )
    )

    confidence = max(
        buy_probability,
        hold_probability,
        sell_probability,
    )

    if position == 1:
        signal = "buy"

    elif position == -1:
        signal = "sell"

    else:
        signal = "hold"

    decision_id = (
        "v39-"
        + uuid4().hex
    )

    decision = {
        "decision_id": (
            decision_id
        ),
        "timestamp": (
            timestamp.isoformat()
        ),
        "symbol": (
            settings
            .v39_learning_symbol
        ),
        "interval": (
            settings
            .v39_learning_interval
        ),
        "signal": signal,
        "confidence": (
            confidence
        ),
        "buy_probability": (
            buy_probability
        ),
        "hold_probability": (
            hold_probability
        ),
        "sell_probability": (
            sell_probability
        ),
        "model_name": (
            metadata.get(
                "model_name"
            )
        ),
        "learning_architecture": (
            metadata.get(
                "learning_architecture"
            )
        ),
        "long_threshold": (
            long_threshold
        ),
        "short_threshold": (
            short_threshold
        ),
        "should_execute": (
            signal
            in {
                "buy",
                "sell",
            }
        ),
        "reason": (
            "Actionable V3.9 model signal."
            if signal
            in {
                "buy",
                "sell",
            }
            else (
                "V3.9 model selected hold."
            )
        ),
        "market_data_age_seconds": (
            age.total_seconds()
        ),
    }

    append_jsonl(
        path=Path(
            settings
            .v39_decision_log_path
        ),
        payload=decision,
    )

    print()
    print(
        "=== V3.9 EXECUTION DECISION ==="
    )

    print(
        json.dumps(
            decision,
            indent=2,
        )
    )

    if signal == "hold":
        print()
        print(
            "V3.9 cycle completed "
            "without an order."
        )

        return

    account_id = (
        settings
        .v39_account_id
        .strip()
    )

    if not account_id:
        raise RuntimeError(
            "V39_ACCOUNT_ID is required."
        )

    if (
        settings
        .v39_order_quantity
        <= 0.0
    ):
        raise RuntimeError(
            "V39_ORDER_QUANTITY "
            "must be positive."
        )

    client_order_id = (
        "v39-"
        + uuid4().hex
    )

    body = {
        "account_id": (
            account_id
        ),
        "client_order_id": (
            client_order_id
        ),
        "symbol": (
            settings
            .v39_learning_symbol
        ),
        "side": signal,
        "order_type": "market",
        "quantity": (
            settings
            .v39_order_quantity
        ),
        "time_in_force": "day",
    }

    request = Request(
        settings
        .v39_paper_order_url,
        data=json.dumps(
            body
        ).encode(
            "utf-8"
        ),
        headers={
            "Content-Type": (
                "application/json"
            ),
            "Accept": (
                "application/json"
            ),
        },
        method="POST",
    )

    submitted_at = (
        datetime.now(UTC)
    )

    try:
        with urlopen(
            request,
            timeout=30.0,
        ) as response:
            raw_response = (
                response
                .read()
                .decode(
                    "utf-8"
                )
            )

            response_payload = (
                json.loads(
                    raw_response
                )
            )

        execution = {
            "decision_id": (
                decision_id
            ),
            "client_order_id": (
                client_order_id
            ),
            "submitted_at": (
                submitted_at
                .isoformat()
            ),
            "symbol": (
                settings
                .v39_learning_symbol
            ),
            "side": signal,
            "quantity": (
                settings
                .v39_order_quantity
            ),
            "accepted": True,
            "response": (
                response_payload
            ),
        }

    except HTTPError as error:
        raw = (
            error.read()
            .decode(
                "utf-8",
                errors="replace",
            )
        )

        execution = {
            "decision_id": (
                decision_id
            ),
            "client_order_id": (
                client_order_id
            ),
            "submitted_at": (
                submitted_at
                .isoformat()
            ),
            "symbol": (
                settings
                .v39_learning_symbol
            ),
            "side": signal,
            "quantity": (
                settings
                .v39_order_quantity
            ),
            "accepted": False,
            "error": (
                f"HTTP {error.code}: "
                f"{raw}"
            ),
        }

    except (
        URLError,
        TimeoutError,
    ) as error:
        execution = {
            "decision_id": (
                decision_id
            ),
            "client_order_id": (
                client_order_id
            ),
            "submitted_at": (
                submitted_at
                .isoformat()
            ),
            "symbol": (
                settings
                .v39_learning_symbol
            ),
            "side": signal,
            "quantity": (
                settings
                .v39_order_quantity
            ),
            "accepted": False,
            "error": repr(
                error
            ),
        }

    append_jsonl(
        path=Path(
            settings
            .v39_execution_log_path
        ),
        payload=execution,
    )

    print()
    print(
        "=== V3.9 PAPER EXECUTION RESULT ==="
    )

    print(
        json.dumps(
            execution,
            indent=2,
        )
    )

    if execution[
        "accepted"
    ]:
        print()
        print(
            "V3.9 paper order "
            "was accepted."
        )

    else:
        print()
        print(
            "V3.9 paper order "
            "was not accepted."
        )

        error = execution.get(
            "error"
        )

        if error:
            print(
                "Reason:",
                error,
            )


if __name__ == "__main__":
    main()