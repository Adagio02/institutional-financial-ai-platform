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

from finai.application.services.v38_learning_factory import (
    create_v38_learning_service,
)
from finai.application.services.v38_learning_service import (
    V38LearningService,
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

    if not settings.v38_execution_enabled:
        print(
            "V3.8 execution is disabled."
        )

        return

    if settings.v38_live_money_enabled:
        raise RuntimeError(
            "V3.8 refuses live-money execution."
        )

    if settings.execution_mode != "alpaca_paper":
        raise RuntimeError(
            "V3.8 requires alpaca_paper mode."
        )

    service = (
        create_v38_learning_service(
            settings=settings
        )
    )

    champion_path = Path(
        settings
        .v38_learning_artifact_directory
    ) / "champion.joblib"

    metadata_path = Path(
        settings
        .v38_learning_artifact_directory
    ) / "champion.json"

    if not champion_path.exists():
        print(
            "V3.8 cycle blocked safely:"
        )

        print(
            "No qualified V3.8 champion exists."
        )

        return

    if not metadata_path.exists():
        print(
            "V3.8 cycle blocked safely:"
        )

        print(
            "Champion metadata does not exist."
        )

        return

    dataset, _ = (
        service.build_dataset(
            symbol=(
                settings
                .v38_learning_symbol
            ),
            interval=(
                settings
                .v38_learning_interval
            ),
            include_target=False,
        )
    )

    if dataset.empty:
        raise RuntimeError(
            "No live V3.8 feature row exists."
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

    if age > timedelta(
        seconds=(
            settings
            .v38_maximum_market_data_age_seconds
        )
    ):
        print(
            "V3.8 cycle completed without order."
        )

        print(
            "Reason: Market data is stale."
        )

        return

    metadata = json.loads(
        metadata_path.read_text(
            encoding="utf-8"
        )
    )

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
            long_threshold=float(
                metadata[
                    "long_threshold"
                ]
            ),
            short_threshold=float(
                metadata[
                    "short_threshold"
                ]
            ),
        )
    )

    position = int(
        positions[0]
    )

    if position == 1:
        signal = "buy"

    elif position == -1:
        signal = "sell"

    else:
        signal = "hold"

    decision_id = (
        "v38-"
        + uuid4().hex
    )

    decision = {
        "decision_id": decision_id,
        "timestamp": (
            timestamp.isoformat()
        ),
        "symbol": (
            settings
            .v38_learning_symbol
        ),
        "signal": signal,
        "model_name": (
            metadata.get(
                "model_name"
            )
        ),
        "long_threshold": (
            metadata.get(
                "long_threshold"
            )
        ),
        "short_threshold": (
            metadata.get(
                "short_threshold"
            )
        ),
        "should_execute": (
            signal
            in {
                "buy",
                "sell",
            }
        ),
    }

    append_jsonl(
        path=Path(
            settings
            .v38_decision_log_path
        ),
        payload=decision,
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
            "V3.8 cycle completed "
            "without an order."
        )

        return

    if not settings.v38_account_id:
        raise RuntimeError(
            "V38_ACCOUNT_ID is required."
        )

    client_order_id = (
        "v38-"
        + uuid4().hex
    )

    body = {
        "account_id": (
            settings
            .v38_account_id
        ),
        "client_order_id": (
            client_order_id
        ),
        "symbol": (
            settings
            .v38_learning_symbol
        ),
        "side": signal,
        "order_type": "market",
        "quantity": (
            settings
            .v38_order_quantity
        ),
        "time_in_force": "day",
    }

    request = Request(
        settings
        .v38_paper_order_url,
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
            response_payload = (
                json.loads(
                    response
                    .read()
                    .decode(
                        "utf-8"
                    )
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
            "accepted": False,
            "error": repr(
                error
            ),
        }

    append_jsonl(
        path=Path(
            settings
            .v38_execution_log_path
        ),
        payload=execution,
    )

    print()
    print(
        json.dumps(
            execution,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()