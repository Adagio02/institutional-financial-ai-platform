from __future__ import annotations

import json
from dataclasses import (
    asdict,
)
from datetime import (
    UTC,
    datetime,
    timedelta,
)
from pathlib import Path
from typing import Any
from urllib.error import (
    HTTPError,
    URLError,
)
from urllib.request import (
    Request,
    urlopen,
)
from uuid import (
    uuid4,
)

import joblib
import pandas as pd

from finai.domain.learning.v33_features import (
    FEATURE_COLUMNS,
)
from finai.domain.learning.v33_thresholds import (
    probabilities_to_positions,
)
from finai.domain.learning.v36_execution import (
    V36ExecutionDecision,
    V36ExecutionResult,
)


BUY = 1
HOLD = 0
SELL = -1


class V36PaperExecutionService:
    def __init__(
        self,
        *,
        champion_directory: str,
        paper_order_url: str,
        account_id: str,
        quantity: float,
        minimum_execution_confidence: float,
        cooldown_seconds: int,
        maximum_market_data_age_seconds: int,
        decision_log_path: str,
        execution_log_path: str,
        live_money_enabled: bool,
    ) -> None:
        if live_money_enabled:
            raise RuntimeError(
                "V3.6 does not permit live-money "
                "execution."
            )

        if quantity <= 0.0:
            raise ValueError(
                "quantity must be positive."
            )

        if not (
            0.0
            <= minimum_execution_confidence
            <= 1.0
        ):
            raise ValueError(
                "minimum_execution_confidence must "
                "be between zero and one."
            )

        if cooldown_seconds < 0:
            raise ValueError(
                "cooldown_seconds cannot be negative."
            )

        if maximum_market_data_age_seconds <= 0:
            raise ValueError(
                "maximum_market_data_age_seconds "
                "must be positive."
            )

        self._champion_directory = Path(
            champion_directory
        )

        self._paper_order_url = (
            paper_order_url
            .strip()
        )

        self._account_id = (
            account_id
            .strip()
        )

        self._quantity = (
            quantity
        )

        self._minimum_execution_confidence = (
            minimum_execution_confidence
        )

        self._cooldown_seconds = (
            cooldown_seconds
        )

        self._maximum_market_data_age_seconds = (
            maximum_market_data_age_seconds
        )

        self._decision_log_path = Path(
            decision_log_path
        )

        self._execution_log_path = Path(
            execution_log_path
        )

        self._last_execution_at: (
            datetime | None
        ) = None

        if not self._account_id:
            raise ValueError(
                "V3.6 account_id is required."
            )

    @property
    def champion_model_path(
        self,
    ) -> Path:
        return (
            self._champion_directory
            / "champion.joblib"
        )

    @property
    def champion_metadata_path(
        self,
    ) -> Path:
        return (
            self._champion_directory
            / "champion.json"
        )

    def _load_champion(
        self,
    ) -> tuple[
        Any,
        dict[str, Any],
    ]:
        if not (
            self.champion_model_path
            .exists()
        ):
            raise FileNotFoundError(
                "No V3.6-compatible champion "
                "model exists."
            )

        if not (
            self.champion_metadata_path
            .exists()
        ):
            raise FileNotFoundError(
                "Champion metadata does not exist."
            )

        model = joblib.load(
            self.champion_model_path
        )

        metadata = json.loads(
            self
            .champion_metadata_path
            .read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(
            metadata,
            dict,
        ):
            raise RuntimeError(
                "Champion metadata is invalid."
            )

        return (
            model,
            metadata,
        )

    @staticmethod
    def _normalize_timestamp(
        value: Any,
    ) -> datetime:
        timestamp = pd.Timestamp(
            value
        ).to_pydatetime()

        if timestamp.tzinfo is None:
            timestamp = (
                timestamp.replace(
                    tzinfo=UTC
                )
            )

        return timestamp.astimezone(
            UTC
        )

    def decide(
        self,
        *,
        symbol: str,
        interval: str,
        latest_feature_row: pd.DataFrame,
        latest_timestamp: Any,
        reference_price: float,
        provider: str,
    ) -> V36ExecutionDecision:
        normalized_symbol = (
            symbol
            .strip()
            .upper()
        )

        normalized_provider = (
            provider
            .strip()
            .lower()
        )

        timestamp = (
            self._normalize_timestamp(
                latest_timestamp
            )
        )

        now = datetime.now(
            UTC
        )

        decision_id = (
            "v36-"
            + uuid4().hex
        )

        if normalized_provider != "alpaca":
            decision = (
                V36ExecutionDecision(
                    decision_id=decision_id,
                    symbol=normalized_symbol,
                    interval=interval,
                    timestamp=timestamp,
                    signal="hold",
                    confidence=0.0,
                    reference_price=(
                        reference_price
                    ),
                    quantity=(
                        self._quantity
                    ),
                    should_execute=False,
                    reason=(
                        "Market data provider "
                        "is not Alpaca."
                    ),
                )
            )

            self._record_decision(
                decision
            )

            return decision

        age = (
            now
            - timestamp
        )

        if age > timedelta(
            seconds=(
                self
                ._maximum_market_data_age_seconds
            )
        ):
            decision = (
                V36ExecutionDecision(
                    decision_id=decision_id,
                    symbol=normalized_symbol,
                    interval=interval,
                    timestamp=timestamp,
                    signal="hold",
                    confidence=0.0,
                    reference_price=(
                        reference_price
                    ),
                    quantity=(
                        self._quantity
                    ),
                    should_execute=False,
                    reason=(
                        "Market data is stale."
                    ),
                )
            )

            self._record_decision(
                decision
            )

            return decision

        model, metadata = (
            self._load_champion()
        )

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

        probabilities = (
            model.predict_proba(
                latest_feature_row[
                    FEATURE_COLUMNS
                ]
            )
        )

        positions = (
            probabilities_to_positions(
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

        probability_map = {
            int(label): float(
                probability
            )
            for (
                label,
                probability,
            )
            in zip(
                model.classes_,
                probabilities[
                    0
                ],
                strict=True,
            )
        }

        if position == BUY:
            signal = "buy"

            confidence = (
                probability_map.get(
                    BUY,
                    0.0,
                )
            )

        elif position == SELL:
            signal = "sell"

            confidence = (
                probability_map.get(
                    SELL,
                    0.0,
                )
            )

        else:
            signal = "hold"

            confidence = (
                probability_map.get(
                    HOLD,
                    max(
                        probability_map
                        .values()
                    ),
                )
            )

        should_execute = (
            signal
            in {
                "buy",
                "sell",
            }
            and confidence
            >= (
                self
                ._minimum_execution_confidence
            )
        )

        reason = (
            "Champion generated an executable "
            "paper signal."
            if should_execute
            else (
                "Signal is HOLD or confidence "
                "is below execution minimum."
            )
        )

        if (
            should_execute
            and self._last_execution_at
            is not None
        ):
            elapsed = (
                now
                - self._last_execution_at
            )

            if elapsed < timedelta(
                seconds=(
                    self
                    ._cooldown_seconds
                )
            ):
                should_execute = False

                reason = (
                    "Execution cooldown "
                    "is active."
                )

        decision = (
            V36ExecutionDecision(
                decision_id=decision_id,
                symbol=normalized_symbol,
                interval=interval,
                timestamp=timestamp,
                signal=signal,
                confidence=(
                    confidence
                ),
                reference_price=(
                    reference_price
                ),
                quantity=(
                    self._quantity
                ),
                should_execute=(
                    should_execute
                ),
                reason=reason,
            )
        )

        self._record_decision(
            decision
        )

        return decision

    def submit(
        self,
        *,
        decision: V36ExecutionDecision,
    ) -> V36ExecutionResult:
        if not decision.should_execute:
            raise ValueError(
                "Decision is not executable."
            )

        if decision.signal not in {
            "buy",
            "sell",
        }:
            raise ValueError(
                "Unsupported V3.6 signal."
            )

        client_order_id = (
            "v36-"
            + uuid4().hex
        )

        body = {
            "account_id": (
                self._account_id
            ),
            "client_order_id": (
                client_order_id
            ),
            "symbol": (
                decision.symbol
            ),
            "side": (
                decision.signal
            ),
            "order_type": "market",
            "quantity": (
                decision.quantity
            ),
            "time_in_force": "day",
        }

        request = Request(
            self._paper_order_url,
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
            datetime.now(
                UTC
            )
        )

        try:
            with urlopen(
                request,
                timeout=30.0,
            ) as response:
                payload = json.loads(
                    response
                    .read()
                    .decode(
                        "utf-8"
                    )
                )

            result = (
                V36ExecutionResult(
                    decision_id=(
                        decision.decision_id
                    ),
                    client_order_id=(
                        client_order_id
                    ),
                    symbol=(
                        decision.symbol
                    ),
                    side=(
                        decision.signal
                    ),
                    quantity=(
                        decision.quantity
                    ),
                    submitted_at=(
                        submitted_at
                    ),
                    accepted=True,
                    order_id=str(
                        payload.get(
                            "id"
                        )
                    )
                    if payload.get(
                        "id"
                    )
                    is not None
                    else None,
                    broker_order_id=str(
                        payload.get(
                            "broker_order_id"
                        )
                    )
                    if payload.get(
                        "broker_order_id"
                    )
                    is not None
                    else None,
                    status=(
                        payload.get(
                            "status"
                        )
                    ),
                    error=None,
                )
            )

            self._last_execution_at = (
                submitted_at
            )

        except HTTPError as error:
            raw = (
                error.read()
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )

            result = (
                V36ExecutionResult(
                    decision_id=(
                        decision.decision_id
                    ),
                    client_order_id=(
                        client_order_id
                    ),
                    symbol=(
                        decision.symbol
                    ),
                    side=(
                        decision.signal
                    ),
                    quantity=(
                        decision.quantity
                    ),
                    submitted_at=(
                        submitted_at
                    ),
                    accepted=False,
                    order_id=None,
                    broker_order_id=None,
                    status=None,
                    error=(
                        "HTTP "
                        f"{error.code}: "
                        f"{raw}"
                    ),
                )
            )

        except (
            URLError,
            TimeoutError,
        ) as error:
            result = (
                V36ExecutionResult(
                    decision_id=(
                        decision.decision_id
                    ),
                    client_order_id=(
                        client_order_id
                    ),
                    symbol=(
                        decision.symbol
                    ),
                    side=(
                        decision.signal
                    ),
                    quantity=(
                        decision.quantity
                    ),
                    submitted_at=(
                        submitted_at
                    ),
                    accepted=False,
                    order_id=None,
                    broker_order_id=None,
                    status=None,
                    error=repr(
                        error
                    ),
                )
            )

        self._record_execution(
            result
        )

        return result

    def _record_decision(
        self,
        decision: V36ExecutionDecision,
    ) -> None:
        self._append_jsonl(
            path=(
                self._decision_log_path
            ),
            payload=(
                asdict(
                    decision
                )
            ),
        )

    def _record_execution(
        self,
        result: V36ExecutionResult,
    ) -> None:
        self._append_jsonl(
            path=(
                self._execution_log_path
            ),
            payload=(
                asdict(
                    result
                )
            ),
        )

    @staticmethod
    def _append_jsonl(
        *,
        path: Path,
        payload: dict[str, Any],
    ) -> None:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        normalized = {}

        for key, value in (
            payload.items()
        ):
            if isinstance(
                value,
                datetime,
            ):
                normalized[
                    key
                ] = (
                    value
                    .astimezone(UTC)
                    .isoformat()
                )

            else:
                normalized[
                    key
                ] = value

        with path.open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    normalized,
                    sort_keys=True,
                )
            )

            handle.write(
                "\n"
            )