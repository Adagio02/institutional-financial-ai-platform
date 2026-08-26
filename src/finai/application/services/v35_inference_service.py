from __future__ import annotations

import json
from dataclasses import asdict
from datetime import (
    UTC,
    datetime,
)
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from finai.domain.learning.v35_inference import (
    V35Prediction,
)


def determine_signal(
    *,
    predicted_class: int,
    confidence: float,
    minimum_confidence: float,
) -> str:
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(
            "confidence must be between 0 and 1."
        )

    if not 0.0 <= minimum_confidence <= 1.0:
        raise ValueError(
            "minimum_confidence must be between 0 and 1."
        )

    if confidence < minimum_confidence:
        return "hold"

    if predicted_class == 1:
        return "long"

    if predicted_class == -1:
        return "short"

    if predicted_class == 0:
        return "hold"

    raise ValueError(
        "Unsupported predicted class: "
        f"{predicted_class}"
    )


class V35InferenceService:
    def __init__(
        self,
        *,
        champion_directory: str,
        prediction_log_path: str,
        minimum_confidence: float,
        require_alpaca_data: bool,
    ) -> None:
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError(
                "minimum_confidence must be "
                "between 0 and 1."
            )

        self._champion_directory = Path(
            champion_directory
        )

        self._prediction_log_path = Path(
            prediction_log_path
        )

        self._minimum_confidence = (
            minimum_confidence
        )

        self._require_alpaca_data = (
            require_alpaca_data
        )

    def load_champion_metadata(
        self,
    ) -> dict[str, Any]:
        metadata_path = (
            self._champion_directory
            / "champion.json"
        )

        if not metadata_path.exists():
            raise RuntimeError(
                "No promoted champion exists. "
                "V3.5 inference will not fabricate "
                "or force a champion."
            )

        with metadata_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            metadata = json.load(
                file
            )

        if not isinstance(
            metadata,
            dict,
        ):
            raise RuntimeError(
                "Champion metadata is invalid."
            )

        return metadata

    def load_champion(
        self,
    ) -> tuple[
        Any,
        dict[str, Any],
        Path,
    ]:
        metadata = (
            self.load_champion_metadata()
        )

        raw_model_path = (
            metadata.get("model_path")
            or metadata.get("champion_path")
            or metadata.get("path")
        )

        if not raw_model_path:
            raise RuntimeError(
                "Champion metadata does not "
                "contain a model path."
            )

        model_path = Path(
            str(raw_model_path)
        )

        if not model_path.is_absolute():
            if not model_path.exists():
                candidate = (
                    self._champion_directory
                    / model_path.name
                )

                model_path = candidate

        if not model_path.exists():
            raise RuntimeError(
                "Champion model file does "
                "not exist: "
                f"{model_path}"
            )

        model = joblib.load(
            model_path
        )

        return (
            model,
            metadata,
            model_path,
        )

    def predict(
        self,
        *,
        symbol: str,
        interval: str,
        feature_row: Any,
        timestamp: datetime,
        provider: str,
    ) -> V35Prediction:
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

        if not normalized_symbol:
            raise ValueError(
                "symbol cannot be blank."
            )

        if (
            self._require_alpaca_data
            and normalized_provider
            != "alpaca"
        ):
            raise RuntimeError(
                "V3.5 requires Alpaca "
                "market data."
            )

        model, metadata, model_path = (
            self.load_champion()
        )

        probabilities = (
            model.predict_proba(
                feature_row
            )[0]
        )

        classes = list(
            model.classes_
        )

        probability_by_class = {
            int(model_class): float(
                probability
            )
            for model_class, probability
            in zip(
                classes,
                probabilities,
                strict=True,
            )
        }

        predicted_index = int(
            np.argmax(
                probabilities
            )
        )

        predicted_class = int(
            classes[
                predicted_index
            ]
        )

        confidence = float(
            probabilities[
                predicted_index
            ]
        )

        signal = determine_signal(
            predicted_class=(
                predicted_class
            ),
            confidence=confidence,
            minimum_confidence=(
                self._minimum_confidence
            ),
        )

        prediction = V35Prediction(
            symbol=normalized_symbol,
            interval=interval,
            timestamp=(
                timestamp
                if timestamp.tzinfo
                else timestamp.replace(
                    tzinfo=UTC
                )
            ),
            predicted_class=(
                predicted_class
            ),
            short_probability=(
                probability_by_class.get(
                    -1,
                    0.0,
                )
            ),
            neutral_probability=(
                probability_by_class.get(
                    0,
                    0.0,
                )
            ),
            long_probability=(
                probability_by_class.get(
                    1,
                    0.0,
                )
            ),
            confidence=confidence,
            signal=signal,
            model_name=str(
                metadata.get(
                    "model_name",
                    type(model).__name__,
                )
            ),
            model_path=str(
                model_path
            ),
            market_data_provider=(
                normalized_provider
            ),
        )

        self._record_prediction(
            prediction
        )

        return prediction

    def _record_prediction(
        self,
        prediction: V35Prediction,
    ) -> None:
        self._prediction_log_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = asdict(
            prediction
        )

        payload["timestamp"] = (
            prediction.timestamp
            .astimezone(UTC)
            .isoformat()
        )

        with self._prediction_log_path.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                json.dumps(
                    payload,
                    sort_keys=True,
                )
            )

            file.write(
                "\n"
            )