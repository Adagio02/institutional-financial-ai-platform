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
from sklearn.ensemble import (
    RandomForestClassifier,
)
from sklearn.linear_model import (
    LogisticRegression,
)
from sklearn.metrics import (
    balanced_accuracy_score,
    f1_score,
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
from sklearn.base import clone

from finai.domain.learning.v31_promotion import (
    V31PromotionDecision,
    V31PromotionMetrics,
    V31PromotionPolicy,
)


HOLD = 0
BUY = 1
SELL = -1


FEATURE_COLUMNS = [
    "return_1",
    "return_3",
    "return_5",
    "return_10",
    "momentum_5",
    "momentum_10",
    "momentum_20",
    "volatility_5",
    "volatility_10",
    "volatility_20",
    "range_pct",
    "body_pct",
    "upper_wick_pct",
    "lower_wick_pct",
    "volume_change_1",
    "volume_ratio_5",
    "volume_ratio_20",
    "distance_sma_5",
    "distance_sma_20",
    "intraday_sin",
    "intraday_cos",
]


@dataclass(
    frozen=True,
    slots=True,
)
class V31FoldMetrics:
    fold: int

    balanced_accuracy: float
    macro_f1: float

    gross_return: float
    transaction_cost: float
    net_return: float

    trade_count: int


@dataclass(
    frozen=True,
    slots=True,
)
class V31ModelEvaluation:
    model_name: str

    balanced_accuracy: float
    macro_f1: float

    gross_return: float
    transaction_cost: float
    net_return: float

    trade_count: int

    composite_score: float

    folds: list[V31FoldMetrics]


@dataclass(
    frozen=True,
    slots=True,
)
class V31LearningCycleResult:
    symbol: str
    interval: str

    rows_loaded: int
    rows_used: int

    winning_model: str

    balanced_accuracy: float
    macro_f1: float

    gross_return: float
    transaction_cost: float
    net_return: float

    trade_count: int

    composite_score: float

    champion_score: float | None

    promoted: bool
    promotion_reason: str

    candidate_path: str
    champion_path: str | None

    completed_at: str


@dataclass(
    frozen=True,
    slots=True,
)
class V31Signal:
    symbol: str
    interval: str

    timestamp: str

    buy_probability: float
    hold_probability: float
    sell_probability: float

    signal: str

    confidence: float

    model_path: str


class V31LearningService:
    def __init__(
        self,
        *,
        database_url: str,
        artifact_directory: str,
        minimum_rows: int,
        forward_horizon_bars: int,
        target_minimum_edge_bps: float,
        round_trip_cost_bps: float,
        walk_forward_folds: int,
        minimum_balanced_accuracy: float,
        minimum_macro_f1: float,
        minimum_net_return: float,
        minimum_trades: int,
        minimum_promotion_improvement: float,
        signal_probability_threshold: float,
        require_non_mock_data: bool,
    ) -> None:
        if minimum_rows < 500:
            raise ValueError(
                "minimum_rows must be at least 500."
            )

        if forward_horizon_bars <= 0:
            raise ValueError(
                "forward_horizon_bars must "
                "be positive."
            )

        if target_minimum_edge_bps <= 0.0:
            raise ValueError(
                "target_minimum_edge_bps must "
                "be positive."
            )

        if round_trip_cost_bps < 0.0:
            raise ValueError(
                "round_trip_cost_bps cannot "
                "be negative."
            )

        if walk_forward_folds < 2:
            raise ValueError(
                "walk_forward_folds must "
                "be at least 2."
            )

        if not (
            0.50
            <= signal_probability_threshold
            < 1.0
        ):
            raise ValueError(
                "signal_probability_threshold must "
                "be between 0.50 and 1.0."
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

        self._forward_horizon_bars = (
            forward_horizon_bars
        )

        self._target_minimum_edge_bps = (
            target_minimum_edge_bps
        )

        self._round_trip_cost_bps = (
            round_trip_cost_bps
        )

        self._walk_forward_folds = (
            walk_forward_folds
        )

        self._signal_probability_threshold = (
            signal_probability_threshold
        )

        self._require_non_mock_data = (
            require_non_mock_data
        )

        self._promotion_policy = (
            V31PromotionPolicy(
                minimum_balanced_accuracy=(
                    minimum_balanced_accuracy
                ),
                minimum_macro_f1=(
                    minimum_macro_f1
                ),
                minimum_net_return=(
                    minimum_net_return
                ),
                minimum_trades=(
                    minimum_trades
                ),
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
                "No eligible V3.1 market data "
                "was found."
            )

        return frame

    def build_features(
        self,
        frame: pd.DataFrame,
        *,
        include_target: bool,
    ) -> pd.DataFrame:
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

        timestamp = pd.to_datetime(
            result["timestamp"],
            utc=True,
        )

        close = result["close_price"]
        open_price = result["open_price"]
        high = result["high_price"]
        low = result["low_price"]
        volume = result["volume"]

        result["return_1"] = (
            close.pct_change(1)
        )

        result["return_3"] = (
            close.pct_change(3)
        )

        result["return_5"] = (
            close.pct_change(5)
        )

        result["return_10"] = (
            close.pct_change(10)
        )

        result["momentum_5"] = (
            close
            / close.shift(5)
            - 1.0
        )

        result["momentum_10"] = (
            close
            / close.shift(10)
            - 1.0
        )

        result["momentum_20"] = (
            close
            / close.shift(20)
            - 1.0
        )

        result["volatility_5"] = (
            result["return_1"]
            .rolling(5)
            .std()
        )

        result["volatility_10"] = (
            result["return_1"]
            .rolling(10)
            .std()
        )

        result["volatility_20"] = (
            result["return_1"]
            .rolling(20)
            .std()
        )

        result["range_pct"] = (
            (high - low)
            / close
        )

        result["body_pct"] = (
            (close - open_price)
            / open_price
        )

        body_high = pd.concat(
            [
                open_price,
                close,
            ],
            axis=1,
        ).max(
            axis=1
        )

        body_low = pd.concat(
            [
                open_price,
                close,
            ],
            axis=1,
        ).min(
            axis=1
        )

        result["upper_wick_pct"] = (
            (high - body_high)
            / close
        )

        result["lower_wick_pct"] = (
            (body_low - low)
            / close
        )

        result["volume_change_1"] = (
            volume.pct_change()
        )

        result["volume_ratio_5"] = (
            volume
            / volume.rolling(5).mean()
        )

        result["volume_ratio_20"] = (
            volume
            / volume.rolling(20).mean()
        )

        sma_5 = (
            close
            .rolling(5)
            .mean()
        )

        sma_20 = (
            close
            .rolling(20)
            .mean()
        )

        result["distance_sma_5"] = (
            close
            / sma_5
            - 1.0
        )

        result["distance_sma_20"] = (
            close
            / sma_20
            - 1.0
        )

        minute_of_day = (
            timestamp.dt.hour * 60
            + timestamp.dt.minute
        )

        angle = (
            2.0
            * np.pi
            * minute_of_day
            / 1440.0
        )

        result["intraday_sin"] = (
            np.sin(angle)
        )

        result["intraday_cos"] = (
            np.cos(angle)
        )

        result.replace(
            [
                np.inf,
                -np.inf,
            ],
            np.nan,
            inplace=True,
        )

        if include_target:
            future_close = close.shift(
                -self._forward_horizon_bars
            )

            result[
                "forward_return"
            ] = (
                future_close
                / close
                - 1.0
            )

            edge = (
                self._target_minimum_edge_bps
                / 10_000.0
            )

            result["target"] = HOLD

            result.loc[
                result["forward_return"]
                > edge,
                "target",
            ] = BUY

            result.loc[
                result["forward_return"]
                < -edge,
                "target",
            ] = SELL

            result = result.dropna(
                subset=(
                    FEATURE_COLUMNS
                    + [
                        "forward_return",
                    ]
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
    def create_models(
    ) -> dict[str, Any]:
        return {
            "logistic_regression": (
                Pipeline(
                    steps=[
                        (
                            "scaler",
                            StandardScaler(),
                        ),
                        (
                            "classifier",
                            LogisticRegression(
                                max_iter=3000,
                                class_weight=(
                                    "balanced"
                                ),
                                random_state=42,
                            ),
                        ),
                    ]
                )
            ),
            "random_forest": (
                RandomForestClassifier(
                    n_estimators=300,
                    max_depth=8,
                    min_samples_leaf=10,
                    class_weight=(
                        "balanced_subsample"
                    ),
                    random_state=42,
                    n_jobs=-1,
                )
            ),
        }

    def _walk_forward_ranges(
        self,
        *,
        rows: int,
    ) -> list[
        tuple[
            int,
            int,
            int,
            int,
        ]
    ]:
        minimum_train = int(
            rows * 0.50
        )

        remaining = (
            rows
            - minimum_train
        )

        fold_size = (
            remaining
            // self._walk_forward_folds
        )

        if fold_size <= 0:
            raise ValueError(
                "Insufficient rows for "
                "walk-forward validation."
            )

        ranges = []

        for fold in range(
            self._walk_forward_folds
        ):
            train_start = 0

            train_end = (
                minimum_train
                + fold
                * fold_size
            )

            validation_start = (
                train_end
            )

            if (
                fold
                == self._walk_forward_folds
                - 1
            ):
                validation_end = rows

            else:
                validation_end = (
                    validation_start
                    + fold_size
                )

            if (
                validation_end
                <= validation_start
            ):
                continue

            ranges.append(
                (
                    train_start,
                    train_end,
                    validation_start,
                    validation_end,
                )
            )

        return ranges

    def _simulate_predictions(
        self,
        *,
        predictions: np.ndarray,
        forward_returns: np.ndarray,
    ) -> tuple[
        float,
        float,
        float,
        int,
    ]:
        positions = predictions.astype(
            float
        )

        gross_values = (
            positions
            * forward_returns
        )

        trade_mask = (
            positions != HOLD
        )

        trade_count = int(
            np.sum(
                trade_mask
            )
        )

        transaction_cost = (
            trade_count
            * (
                self._round_trip_cost_bps
                / 10_000.0
            )
        )

        gross_return = float(
            np.sum(
                gross_values
            )
        )

        net_return = (
            gross_return
            - transaction_cost
        )

        return (
            gross_return,
            transaction_cost,
            net_return,
            trade_count,
        )

    @staticmethod
    def _composite_score(
        *,
        balanced_accuracy: float,
        macro_f1: float,
        net_return: float,
        trade_count: int,
    ) -> float:
        bounded_return = float(
            np.tanh(
                net_return
            )
        )

        trade_component = min(
            trade_count / 100.0,
            1.0,
        )

        return float(
            0.35
            * balanced_accuracy
            + 0.30
            * macro_f1
            + 0.30
            * bounded_return
            + 0.05
            * trade_component
        )

    def evaluate_model(
        self,
        *,
        model_name: str,
        model_template: Any,
        dataset: pd.DataFrame,
    ) -> V31ModelEvaluation:
        fold_results = []

        all_actual: list[int] = []
        all_predictions: list[int] = []

        gross_return = 0.0
        transaction_cost = 0.0
        net_return = 0.0
        trade_count = 0

        ranges = (
            self._walk_forward_ranges(
                rows=len(dataset)
            )
        )

        for fold_number, (
            train_start,
            train_end,
            validation_start,
            validation_end,
        ) in enumerate(
            ranges,
            start=1,
        ):
            train = dataset.iloc[
                train_start:train_end
            ]

            validation = dataset.iloc[
                validation_start:validation_end
            ]

            model = clone(
                model_template
            )

            model.fit(
                train[
                    FEATURE_COLUMNS
                ],
                train[
                    "target"
                ],
            )

            predictions = (
                model.predict(
                    validation[
                        FEATURE_COLUMNS
                    ]
                )
            )

            actual = (
                validation[
                    "target"
                ]
                .to_numpy()
            )

            balanced_accuracy = float(
                balanced_accuracy_score(
                    actual,
                    predictions,
                )
            )

            macro_f1 = float(
                f1_score(
                    actual,
                    predictions,
                    average="macro",
                    zero_division=0,
                )
            )

            (
                fold_gross,
                fold_cost,
                fold_net,
                fold_trades,
            ) = self._simulate_predictions(
                predictions=predictions,
                forward_returns=(
                    validation[
                        "forward_return"
                    ]
                    .to_numpy()
                ),
            )

            fold_results.append(
                V31FoldMetrics(
                    fold=fold_number,
                    balanced_accuracy=(
                        balanced_accuracy
                    ),
                    macro_f1=macro_f1,
                    gross_return=(
                        fold_gross
                    ),
                    transaction_cost=(
                        fold_cost
                    ),
                    net_return=(
                        fold_net
                    ),
                    trade_count=(
                        fold_trades
                    ),
                )
            )

            all_actual.extend(
                actual.tolist()
            )

            all_predictions.extend(
                predictions.tolist()
            )

            gross_return += (
                fold_gross
            )

            transaction_cost += (
                fold_cost
            )

            net_return += (
                fold_net
            )

            trade_count += (
                fold_trades
            )

        overall_balanced_accuracy = float(
            balanced_accuracy_score(
                all_actual,
                all_predictions,
            )
        )

        overall_macro_f1 = float(
            f1_score(
                all_actual,
                all_predictions,
                average="macro",
                zero_division=0,
            )
        )

        composite = (
            self._composite_score(
                balanced_accuracy=(
                    overall_balanced_accuracy
                ),
                macro_f1=(
                    overall_macro_f1
                ),
                net_return=net_return,
                trade_count=trade_count,
            )
        )

        return V31ModelEvaluation(
            model_name=model_name,
            balanced_accuracy=(
                overall_balanced_accuracy
            ),
            macro_f1=(
                overall_macro_f1
            ),
            gross_return=(
                gross_return
            ),
            transaction_cost=(
                transaction_cost
            ),
            net_return=(
                net_return
            ),
            trade_count=(
                trade_count
            ),
            composite_score=(
                composite
            ),
            folds=fold_results,
        )

    def run_learning_cycle(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> V31LearningCycleResult:
        raw = self.load_market_bars(
            symbol=symbol,
            interval=interval,
        )

        dataset = self.build_features(
            raw,
            include_target=True,
        )

        if (
            len(dataset)
            < self._minimum_rows
        ):
            raise ValueError(
                "Insufficient V3.1 learning rows. "
                f"required={self._minimum_rows}, "
                f"available={len(dataset)}."
            )

        evaluations = []

        models = self.create_models()

        for (
            model_name,
            model,
        ) in models.items():
            evaluation = (
                self.evaluate_model(
                    model_name=model_name,
                    model_template=model,
                    dataset=dataset,
                )
            )

            evaluations.append(
                evaluation
            )

        evaluations.sort(
            key=lambda item: (
                item.composite_score
            ),
            reverse=True,
        )

        winner = evaluations[0]

        winning_model = models[
            winner.model_name
        ]

        winning_model.fit(
            dataset[
                FEATURE_COLUMNS
            ],
            dataset[
                "target"
            ],
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
                f"{timestamp}_"
                f"{winner.model_name}"
                ".joblib"
            )
        )

        joblib.dump(
            winning_model,
            candidate_path,
        )

        champion_score = None

        if (
            self.champion_metadata_path
            .exists()
        ):
            metadata = json.loads(
                self
                .champion_metadata_path
                .read_text(
                    encoding="utf-8"
                )
            )

            raw_score = metadata.get(
                "composite_score"
            )

            if raw_score is not None:
                champion_score = float(
                    raw_score
                )

        promotion_metrics = (
            V31PromotionMetrics(
                balanced_accuracy=(
                    winner
                    .balanced_accuracy
                ),
                macro_f1=(
                    winner.macro_f1
                ),
                net_return=(
                    winner.net_return
                ),
                trade_count=(
                    winner.trade_count
                ),
                composite_score=(
                    winner.composite_score
                ),
            )
        )

        decision: V31PromotionDecision = (
            self._promotion_policy.evaluate(
                candidate=(
                    promotion_metrics
                ),
                champion_score=(
                    champion_score
                ),
            )
        )

        champion_path: str | None = None

        if decision.promote:
            shutil.copyfile(
                candidate_path,
                self.champion_path,
            )

            metadata = {
                "version": "3.1",
                "symbol": (
                    symbol.strip().upper()
                ),
                "interval": (
                    interval.strip().lower()
                ),
                "model_name": (
                    winner.model_name
                ),
                "feature_columns": (
                    FEATURE_COLUMNS
                ),
                "balanced_accuracy": (
                    winner
                    .balanced_accuracy
                ),
                "macro_f1": (
                    winner.macro_f1
                ),
                "gross_return": (
                    winner.gross_return
                ),
                "transaction_cost": (
                    winner
                    .transaction_cost
                ),
                "net_return": (
                    winner.net_return
                ),
                "trade_count": (
                    winner.trade_count
                ),
                "composite_score": (
                    winner
                    .composite_score
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

        result = V31LearningCycleResult(
            symbol=(
                symbol.strip().upper()
            ),
            interval=(
                interval.strip().lower()
            ),
            rows_loaded=len(raw),
            rows_used=len(dataset),
            winning_model=(
                winner.model_name
            ),
            balanced_accuracy=(
                winner.balanced_accuracy
            ),
            macro_f1=(
                winner.macro_f1
            ),
            gross_return=(
                winner.gross_return
            ),
            transaction_cost=(
                winner.transaction_cost
            ),
            net_return=(
                winner.net_return
            ),
            trade_count=(
                winner.trade_count
            ),
            composite_score=(
                winner.composite_score
            ),
            champion_score=(
                champion_score
            ),
            promoted=(
                decision.promote
            ),
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

        evaluation_path = (
            self._artifact_directory
            / (
                "evaluation_"
                f"{timestamp}.json"
            )
        )

        evaluation_path.write_text(
            json.dumps(
                [
                    asdict(
                        evaluation
                    )
                    for evaluation
                    in evaluations
                ],
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
    ) -> V31Signal:
        if not self.champion_path.exists():
            raise FileNotFoundError(
                "No V3.1 champion model exists."
            )

        raw = self.load_market_bars(
            symbol=symbol,
            interval=interval,
        )

        feature_frame = (
            self.build_features(
                raw,
                include_target=False,
            )
        )

        latest = feature_frame.iloc[
            [-1]
        ]

        champion = joblib.load(
            self.champion_path
        )

        probabilities = (
            champion.predict_proba(
                latest[
                    FEATURE_COLUMNS
                ]
            )[0]
        )

        classes = (
            champion.classes_
        )

        probability_by_class = {
            int(label): float(
                probability
            )
            for (
                label,
                probability,
            )
            in zip(
                classes,
                probabilities,
                strict=True,
            )
        }

        buy_probability = (
            probability_by_class.get(
                BUY,
                0.0,
            )
        )

        hold_probability = (
            probability_by_class.get(
                HOLD,
                0.0,
            )
        )

        sell_probability = (
            probability_by_class.get(
                SELL,
                0.0,
            )
        )

        best_class = max(
            probability_by_class,
            key=(
                probability_by_class.get
            ),
        )

        confidence = (
            probability_by_class[
                best_class
            ]
        )

        if (
            confidence
            < self._signal_probability_threshold
        ):
            signal = "hold"

        elif best_class == BUY:
            signal = "buy"

        elif best_class == SELL:
            signal = "sell"

        else:
            signal = "hold"

        timestamp_value = (
            latest.iloc[0][
                "timestamp"
            ]
        )

        result = V31Signal(
            symbol=(
                symbol.strip().upper()
            ),
            interval=(
                interval.strip().lower()
            ),
            timestamp=str(
                timestamp_value
            ),
            buy_probability=(
                buy_probability
            ),
            hold_probability=(
                hold_probability
            ),
            sell_probability=(
                sell_probability
            ),
            signal=signal,
            confidence=confidence,
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
                asdict(result),
                indent=2,
            ),
            encoding="utf-8",
        )

        return result