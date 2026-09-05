from __future__ import annotations

import json
import shutil
from dataclasses import (
    asdict,
    dataclass,
)
from datetime import (
    UTC,
    datetime,
)
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import (
    LogisticRegression,
)
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    log_loss,
)
from sklearn.pipeline import (
    Pipeline,
)
from sklearn.preprocessing import (
    StandardScaler,
)
from sqlalchemy import (
    create_engine,
    text,
)

from finai.domain.learning.promotion_policy import (
    ModelPromotionDecision,
    ModelPromotionPolicy,
)


FEATURE_COLUMNS = [
    "return_1",
    "return_3",
    "return_5",
    "momentum_10",
    "volatility_5",
    "range_pct",
    "body_pct",
    "volume_change",
]


@dataclass(
    frozen=True,
    slots=True,
)
class LearningCycleResult:
    symbol: str
    interval: str

    rows_loaded: int
    rows_used: int

    candidate_accuracy: float
    candidate_balanced_accuracy: float
    candidate_log_loss: float

    champion_balanced_accuracy: float | None

    promoted: bool
    promotion_reason: str

    candidate_path: str
    champion_path: str | None

    completed_at: str


@dataclass(
    frozen=True,
    slots=True,
)
class LearningSignal:
    symbol: str
    interval: str

    timestamp: str

    up_probability: float
    down_probability: float

    signal: str

    model_path: str


class AdaptiveLearningService:
    def __init__(
        self,
        *,
        database_url: str,
        artifact_directory: str,
        minimum_rows: int,
        validation_fraction: float,
        minimum_score: float,
        minimum_promotion_improvement: float,
        signal_probability_threshold: float,
        require_non_mock_data: bool,
    ) -> None:
        if minimum_rows < 100:
            raise ValueError(
                "minimum_rows must be at least 100."
            )

        if not 0.05 <= validation_fraction <= 0.50:
            raise ValueError(
                "validation_fraction must be between "
                "0.05 and 0.50."
            )

        if not 0.50 <= signal_probability_threshold < 1.0:
            raise ValueError(
                "signal_probability_threshold must be "
                "between 0.50 and 1.0."
            )

        self._engine = create_engine(
            database_url
        )

        self._artifact_directory = Path(
            artifact_directory
        )

        self._artifact_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._minimum_rows = minimum_rows
        self._validation_fraction = validation_fraction

        self._signal_probability_threshold = (
            signal_probability_threshold
        )

        self._require_non_mock_data = (
            require_non_mock_data
        )

        self._promotion_policy = (
            ModelPromotionPolicy(
                minimum_score=minimum_score,
                minimum_improvement=(
                    minimum_promotion_improvement
                ),
            )
        )

    @property
    def champion_path(
        self,
    ) -> Path:
        return (
            self._artifact_directory
            / "champion.joblib"
        )

    @property
    def champion_metadata_path(
        self,
    ) -> Path:
        return (
            self._artifact_directory
            / "champion.json"
        )

    def load_market_bars(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> pd.DataFrame:
        normalized_symbol = (
            symbol
            .strip()
            .upper()
        )

        normalized_interval = (
            interval
            .strip()
            .lower()
        )

        if not normalized_symbol:
            raise ValueError(
                "symbol cannot be empty."
            )

        if not normalized_interval:
            raise ValueError(
                "interval cannot be empty."
            )

        provider_clause = ""

        if self._require_non_mock_data:
            provider_clause = (
                "AND mb.provider <> 'mock'"
            )

        statement = text(
            f"""
            SELECT
                mb.timestamp,
                mb.open_price,
                mb.high_price,
                mb.low_price,
                mb.close_price,
                mb.volume,
                mb.provider
            FROM market_bars AS mb
            JOIN instruments AS i
                ON i.id = mb.instrument_id
            WHERE i.symbol = :symbol
              AND mb.interval = :interval
              {provider_clause}
            ORDER BY mb.timestamp ASC
            """
        )

        with self._engine.connect() as connection:
            frame = pd.read_sql(
                statement,
                connection,
                params={
                    "symbol": normalized_symbol,
                    "interval": normalized_interval,
                },
            )

        if frame.empty:
            raise ValueError(
                "No eligible market bars were found. "
                f"symbol={normalized_symbol}, "
                f"interval={normalized_interval}."
            )

        return frame

    @staticmethod
    def build_features(
        frame: pd.DataFrame,
        *,
        include_target: bool,
    ) -> pd.DataFrame:
        required_columns = {
            "timestamp",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
        }

        missing = (
            required_columns
            - set(frame.columns)
        )

        if missing:
            raise ValueError(
                "Market-bar data is missing columns: "
                f"{sorted(missing)}"
            )

        result = frame.copy()

        numeric_columns = [
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
        ]

        for column in numeric_columns:
            result[column] = pd.to_numeric(
                result[column],
                errors="coerce",
            )

        close = result["close_price"]
        open_price = result["open_price"]

        result["return_1"] = close.pct_change()
        result["return_3"] = close.pct_change(
            periods=3
        )
        result["return_5"] = close.pct_change(
            periods=5
        )

        result["momentum_10"] = (
            close
            / close.shift(10)
            - 1.0
        )

        result["volatility_5"] = (
            result["return_1"]
            .rolling(window=5)
            .std()
        )

        result["range_pct"] = (
            (
                result["high_price"]
                - result["low_price"]
            )
            / close
        )

        result["body_pct"] = (
            (
                result["close_price"]
                - open_price
            )
            / open_price
        )

        result["volume_change"] = (
            result["volume"]
            .pct_change()
        )

        result.replace(
            [np.inf, -np.inf],
            np.nan,
            inplace=True,
        )

        if include_target:
            next_close = close.shift(-1)

            result["target"] = np.where(
                next_close.notna(),
                (
                    next_close
                    > close
                ).astype(int),
                np.nan,
            )

            result = result.dropna(
                subset=(
                    FEATURE_COLUMNS
                    + ["target"]
                )
            )

            result["target"] = (
                result["target"]
                .astype(int)
            )

        else:
            result = result.dropna(
                subset=FEATURE_COLUMNS
            )

        return result.reset_index(
            drop=True
        )

    @staticmethod
    def create_candidate_model(
    ) -> Pipeline:
        return Pipeline(
            steps=[
                (
                    "scaler",
                    StandardScaler(),
                ),
                (
                    "classifier",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        random_state=42,
                    ),
                ),
            ]
        )

    @staticmethod
    def _validate_classes(
        target: pd.Series,
    ) -> None:
        unique = sorted(
            target.unique().tolist()
        )

        if unique != [0, 1]:
            raise ValueError(
                "Training data must contain both "
                "target classes 0 and 1."
            )

    @staticmethod
    def _score_model(
        *,
        model: Any,
        features: pd.DataFrame,
        target: pd.Series,
    ) -> dict[str, float]:
        probabilities = (
            model.predict_proba(
                features
            )[:, 1]
        )

        predictions = (
            probabilities
            >= 0.5
        ).astype(int)

        return {
            "accuracy": float(
                accuracy_score(
                    target,
                    predictions,
                )
            ),
            "balanced_accuracy": float(
                balanced_accuracy_score(
                    target,
                    predictions,
                )
            ),
            "log_loss": float(
                log_loss(
                    target,
                    probabilities,
                    labels=[0, 1],
                )
            ),
        }

    def run_learning_cycle(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> LearningCycleResult:
        raw = self.load_market_bars(
            symbol=symbol,
            interval=interval,
        )

        dataset = self.build_features(
            raw,
            include_target=True,
        )

        if len(dataset) < self._minimum_rows:
            raise ValueError(
                "Insufficient learning rows. "
                f"required={self._minimum_rows}, "
                f"available={len(dataset)}."
            )

        split_index = int(
            len(dataset)
            * (
                1.0
                - self._validation_fraction
            )
        )

        if split_index <= 0:
            raise ValueError(
                "Training split is empty."
            )

        train = dataset.iloc[
            :split_index
        ].copy()

        validation = dataset.iloc[
            split_index:
        ].copy()

        if validation.empty:
            raise ValueError(
                "Validation split is empty."
            )

        self._validate_classes(
            train["target"]
        )

        self._validate_classes(
            validation["target"]
        )

        train_features = train[
            FEATURE_COLUMNS
        ]

        train_target = train[
            "target"
        ]

        validation_features = validation[
            FEATURE_COLUMNS
        ]

        validation_target = validation[
            "target"
        ]

        candidate = (
            self.create_candidate_model()
        )

        candidate.fit(
            train_features,
            train_target,
        )

        candidate_metrics = (
            self._score_model(
                model=candidate,
                features=validation_features,
                target=validation_target,
            )
        )

        champion_score = None

        if self.champion_path.exists():
            champion = joblib.load(
                self.champion_path
            )

            champion_metrics = (
                self._score_model(
                    model=champion,
                    features=validation_features,
                    target=validation_target,
                )
            )

            champion_score = (
                champion_metrics[
                    "balanced_accuracy"
                ]
            )

        decision: ModelPromotionDecision = (
            self._promotion_policy.evaluate(
                candidate_score=(
                    candidate_metrics[
                        "balanced_accuracy"
                    ]
                ),
                champion_score=(
                    champion_score
                ),
            )
        )

        timestamp = (
            datetime.now(UTC)
            .strftime(
                "%Y%m%dT%H%M%SZ"
            )
        )

        candidate_path = (
            self._artifact_directory
            / (
                "candidate_"
                f"{timestamp}.joblib"
            )
        )

        joblib.dump(
            candidate,
            candidate_path,
        )

        champion_path: str | None = None

        if decision.promote:
            shutil.copyfile(
                candidate_path,
                self.champion_path,
            )

            metadata = {
                "symbol": (
                    symbol.strip().upper()
                ),
                "interval": (
                    interval.strip().lower()
                ),
                "feature_columns": (
                    FEATURE_COLUMNS
                ),
                "candidate_metrics": (
                    candidate_metrics
                ),
                "previous_champion_score": (
                    champion_score
                ),
                "promotion": (
                    asdict(decision)
                ),
                "promoted_at": (
                    datetime.now(UTC)
                    .isoformat()
                ),
            }

            self.champion_metadata_path.write_text(
                json.dumps(
                    metadata,
                    indent=2,
                ),
                encoding="utf-8",
            )

            champion_path = str(
                self.champion_path
            )

        result = LearningCycleResult(
            symbol=(
                symbol
                .strip()
                .upper()
            ),
            interval=(
                interval
                .strip()
                .lower()
            ),
            rows_loaded=len(raw),
            rows_used=len(dataset),
            candidate_accuracy=(
                candidate_metrics[
                    "accuracy"
                ]
            ),
            candidate_balanced_accuracy=(
                candidate_metrics[
                    "balanced_accuracy"
                ]
            ),
            candidate_log_loss=(
                candidate_metrics[
                    "log_loss"
                ]
            ),
            champion_balanced_accuracy=(
                champion_score
            ),
            promoted=decision.promote,
            promotion_reason=(
                decision.reason
            ),
            candidate_path=str(
                candidate_path
            ),
            champion_path=(
                champion_path
            ),
            completed_at=(
                datetime.now(UTC)
                .isoformat()
            ),
        )

        result_path = (
            self._artifact_directory
            / "latest_learning_cycle.json"
        )

        result_path.write_text(
            json.dumps(
                asdict(result),
                indent=2,
            ),
            encoding="utf-8",
        )

        return result

    def generate_signal(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> LearningSignal:
        if not self.champion_path.exists():
            raise FileNotFoundError(
                "No V3.0 champion model exists."
            )

        raw = self.load_market_bars(
            symbol=symbol,
            interval=interval,
        )

        feature_frame = self.build_features(
            raw,
            include_target=False,
        )

        if feature_frame.empty:
            raise ValueError(
                "No feature row is available "
                "for signal generation."
            )

        latest = feature_frame.iloc[
            [-1]
        ]

        champion = joblib.load(
            self.champion_path
        )

        up_probability = float(
            champion.predict_proba(
                latest[
                    FEATURE_COLUMNS
                ]
            )[0, 1]
        )

        down_probability = (
            1.0
            - up_probability
        )

        threshold = (
            self._signal_probability_threshold
        )

        if up_probability >= threshold:
            signal = "buy"

        elif (
            down_probability
            >= threshold
        ):
            signal = "sell"

        else:
            signal = "hold"

        timestamp_value = (
            latest.iloc[0][
                "timestamp"
            ]
        )

        signal_result = LearningSignal(
            symbol=(
                symbol
                .strip()
                .upper()
            ),
            interval=(
                interval
                .strip()
                .lower()
            ),
            timestamp=str(
                timestamp_value
            ),
            up_probability=(
                up_probability
            ),
            down_probability=(
                down_probability
            ),
            signal=signal,
            model_path=str(
                self.champion_path
            ),
        )

        signal_path = (
            self._artifact_directory
            / "latest_signal.json"
        )

        signal_path.write_text(
            json.dumps(
                asdict(
                    signal_result
                ),
                indent=2,
            ),
            encoding="utf-8",
        )

        return signal_result