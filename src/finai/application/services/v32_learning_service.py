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
from sklearn.base import clone
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import (
    LogisticRegression,
)
from sklearn.metrics import (
    balanced_accuracy_score,
    f1_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import (
    create_engine,
    text,
)

from finai.domain.learning.v32_promotion import (
    V32PromotionDecision,
    V32PromotionMetrics,
    V32PromotionPolicy,
)


SELL = -1
HOLD = 0
BUY = 1


FEATURE_COLUMNS = [
    "return_1",
    "return_3",
    "return_5",
    "return_10",
    "return_20",
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
    "distance_sma_10",
    "distance_sma_20",
    "intraday_sin",
    "intraday_cos",
]


@dataclass(
    frozen=True,
    slots=True,
)
class V32BacktestMetrics:
    gross_return: float
    transaction_cost: float
    net_return: float
    trade_count: int
    turnover: float
    maximum_drawdown: float
    sharpe_like: float


@dataclass(
    frozen=True,
    slots=True,
)
class V32FoldMetrics:
    fold: int
    balanced_accuracy: float
    macro_f1: float
    gross_return: float
    transaction_cost: float
    net_return: float
    trade_count: int
    turnover: float
    maximum_drawdown: float
    sharpe_like: float


@dataclass(
    frozen=True,
    slots=True,
)
class V32ModelEvaluation:
    model_name: str

    balanced_accuracy: float
    macro_f1: float

    gross_return: float
    transaction_cost: float
    net_return: float

    trade_count: int
    turnover: float

    maximum_drawdown: float
    sharpe_like: float

    positive_fold_fraction: float

    composite_score: float

    folds: list[V32FoldMetrics]


@dataclass(
    frozen=True,
    slots=True,
)
class V32LearningCycleResult:
    symbol: str
    interval: str

    rows_loaded: int
    rows_used: int

    research_rows: int
    holdout_rows: int

    winning_model: str

    walk_forward_balanced_accuracy: float
    walk_forward_macro_f1: float
    walk_forward_net_return: float

    holdout_balanced_accuracy: float
    holdout_macro_f1: float

    holdout_gross_return: float
    holdout_transaction_cost: float
    holdout_net_return: float

    holdout_trade_count: int
    holdout_turnover: float
    holdout_maximum_drawdown: float
    holdout_sharpe_like: float

    positive_fold_fraction: float

    baseline_net_return: float
    baseline_composite_score: float

    candidate_composite_score: float
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
class V32Signal:
    symbol: str
    interval: str

    timestamp: str

    buy_probability: float
    hold_probability: float
    sell_probability: float

    signal: str
    confidence: float

    model_path: str


class V32LearningService:
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
        holdout_fraction: float,
        signal_probability_threshold: float,
        minimum_balanced_accuracy: float,
        minimum_macro_f1: float,
        minimum_net_return: float,
        minimum_trades: int,
        maximum_drawdown: float,
        minimum_sharpe_like: float,
        minimum_fold_positive_fraction: float,
        minimum_baseline_improvement: float,
        minimum_promotion_improvement: float,
        require_non_mock_data: bool,
    ) -> None:
        if minimum_rows < 1_000:
            raise ValueError(
                "minimum_rows must be at least 1000."
            )

        if forward_horizon_bars <= 0:
            raise ValueError(
                "forward_horizon_bars must be positive."
            )

        if target_minimum_edge_bps <= 0.0:
            raise ValueError(
                "target_minimum_edge_bps must be positive."
            )

        if round_trip_cost_bps < 0.0:
            raise ValueError(
                "round_trip_cost_bps cannot be negative."
            )

        if walk_forward_folds < 2:
            raise ValueError(
                "walk_forward_folds must be at least 2."
            )

        if not 0.10 <= holdout_fraction <= 0.40:
            raise ValueError(
                "holdout_fraction must be between 0.10 and 0.40."
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

        self._holdout_fraction = (
            holdout_fraction
        )

        self._signal_probability_threshold = (
            signal_probability_threshold
        )

        self._require_non_mock_data = (
            require_non_mock_data
        )

        self._promotion_policy = (
            V32PromotionPolicy(
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
                maximum_drawdown=(
                    maximum_drawdown
                ),
                minimum_sharpe_like=(
                    minimum_sharpe_like
                ),
                minimum_fold_positive_fraction=(
                    minimum_fold_positive_fraction
                ),
                minimum_baseline_improvement=(
                    minimum_baseline_improvement
                ),
                minimum_promotion_improvement=(
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
                "No eligible V3.2 market bars were found."
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

        result["return_1"] = close.pct_change(1)
        result["return_3"] = close.pct_change(3)
        result["return_5"] = close.pct_change(5)
        result["return_10"] = close.pct_change(10)
        result["return_20"] = close.pct_change(20)

        result["momentum_5"] = (
            close / close.shift(5) - 1.0
        )

        result["momentum_10"] = (
            close / close.shift(10) - 1.0
        )

        result["momentum_20"] = (
            close / close.shift(20) - 1.0
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
            (high - low) / close
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

        sma_5 = close.rolling(5).mean()
        sma_10 = close.rolling(10).mean()
        sma_20 = close.rolling(20).mean()

        result["distance_sma_5"] = (
            close / sma_5 - 1.0
        )

        result["distance_sma_10"] = (
            close / sma_10 - 1.0
        )

        result["distance_sma_20"] = (
            close / sma_20 - 1.0
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

        result["intraday_sin"] = np.sin(
            angle
        )

        result["intraday_cos"] = np.cos(
            angle
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

            result["forward_return"] = (
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
                result["forward_return"] > edge,
                "target",
            ] = BUY

            result.loc[
                result["forward_return"] < -edge,
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
                                max_iter=3_000,
                                class_weight="balanced",
                                random_state=42,
                            ),
                        ),
                    ]
                )
            ),
            "random_forest": (
                RandomForestClassifier(
                    n_estimators=400,
                    max_depth=10,
                    min_samples_leaf=10,
                    class_weight="balanced_subsample",
                    random_state=42,
                    n_jobs=-1,
                )
            ),
            "hist_gradient_boosting": (
                HistGradientBoostingClassifier(
                    max_iter=300,
                    learning_rate=0.05,
                    max_leaf_nodes=15,
                    min_samples_leaf=20,
                    random_state=42,
                )
            ),
        }

    @staticmethod
    def _validate_target(
        target: pd.Series,
    ) -> None:
        unique = set(
            int(value)
            for value
            in target.unique()
        )

        required = {
            SELL,
            HOLD,
            BUY,
        }

        if not required.issubset(
            unique
        ):
            raise ValueError(
                "V3.2 target must contain "
                "SELL, HOLD, and BUY classes."
            )

    def _split_research_holdout(
        self,
        *,
        dataset: pd.DataFrame,
    ) -> tuple[
        pd.DataFrame,
        pd.DataFrame,
    ]:
        holdout_rows = max(
            1,
            int(
                len(dataset)
                * self._holdout_fraction
            ),
        )

        research_rows = (
            len(dataset)
            - holdout_rows
        )

        if research_rows <= 0:
            raise ValueError(
                "Research split is empty."
            )

        research = dataset.iloc[
            :research_rows
        ].copy()

        holdout = dataset.iloc[
            research_rows:
        ].copy()

        if holdout.empty:
            raise ValueError(
                "Holdout split is empty."
            )

        return (
            research,
            holdout,
        )

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
        initial_train = int(
            rows * 0.50
        )

        remaining = (
            rows
            - initial_train
        )

        fold_size = (
            remaining
            // self._walk_forward_folds
        )

        if fold_size <= 0:
            raise ValueError(
                "Insufficient rows for "
                "V3.2 walk-forward validation."
            )

        ranges = []

        for fold in range(
            self._walk_forward_folds
        ):
            train_start = 0

            train_end = (
                initial_train
                + fold
                * fold_size
            )

            validation_start = (
                train_end
            )

            if (
                fold
                == self._walk_forward_folds - 1
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

    @staticmethod
    def _predictions_from_probabilities(
        *,
        probabilities: np.ndarray,
        classes: np.ndarray,
        threshold: float,
    ) -> np.ndarray:
        predictions = np.full(
            probabilities.shape[0],
            HOLD,
            dtype=int,
        )

        class_to_column = {
            int(label): index
            for index, label
            in enumerate(classes)
        }

        for row_index in range(
            probabilities.shape[0]
        ):
            row = probabilities[
                row_index
            ]

            best_column = int(
                np.argmax(row)
            )

            best_probability = float(
                row[
                    best_column
                ]
            )

            best_class = int(
                classes[
                    best_column
                ]
            )

            if (
                best_probability >= threshold
                and best_class in {
                    SELL,
                    BUY,
                }
            ):
                predictions[
                    row_index
                ] = best_class

            elif (
                HOLD in class_to_column
                and float(
                    row[
                        class_to_column[
                            HOLD
                        ]
                    ]
                )
                >= threshold
            ):
                predictions[
                    row_index
                ] = HOLD

        return predictions

    def _simulate_positions(
        self,
        *,
        positions: np.ndarray,
        forward_returns: np.ndarray,
    ) -> V32BacktestMetrics:
        if len(positions) != len(
            forward_returns
        ):
            raise ValueError(
                "positions and forward_returns "
                "must have equal length."
            )

        if len(positions) == 0:
            return V32BacktestMetrics(
                gross_return=0.0,
                transaction_cost=0.0,
                net_return=0.0,
                trade_count=0,
                turnover=0.0,
                maximum_drawdown=0.0,
                sharpe_like=0.0,
            )

        previous_position = 0.0

        gross_returns = []
        costs = []

        trade_count = 0
        turnover = 0.0

        one_way_cost = (
            self._round_trip_cost_bps
            / 20_000.0
        )

        for (
            position,
            forward_return,
        ) in zip(
            positions.astype(float),
            forward_returns.astype(float),
            strict=True,
        ):
            position_change = abs(
                position
                - previous_position
            )

            if position_change > 0.0:
                trade_count += 1

            turnover += (
                position_change
            )

            cost = (
                position_change
                * one_way_cost
            )

            gross = (
                position
                * forward_return
            )

            gross_returns.append(
                gross
            )

            costs.append(
                cost
            )

            previous_position = (
                position
            )

        gross_array = np.asarray(
            gross_returns,
            dtype=float,
        )

        cost_array = np.asarray(
            costs,
            dtype=float,
        )

        net_array = (
            gross_array
            - cost_array
        )

        equity_curve = np.cumprod(
            1.0 + net_array
        )

        peaks = np.maximum.accumulate(
            equity_curve
        )

        drawdowns = (
            equity_curve
            / peaks
            - 1.0
        )

        maximum_drawdown = float(
            abs(
                np.min(
                    drawdowns
                )
            )
        )

        mean_return = float(
            np.mean(
                net_array
            )
        )

        standard_deviation = float(
            np.std(
                net_array
            )
        )

        if standard_deviation > 0.0:
            sharpe_like = (
                mean_return
                / standard_deviation
                * np.sqrt(
                    len(
                        net_array
                    )
                )
            )

        else:
            sharpe_like = 0.0

        gross_return = float(
            np.sum(
                gross_array
            )
        )

        transaction_cost = float(
            np.sum(
                cost_array
            )
        )

        net_return = float(
            np.sum(
                net_array
            )
        )

        return V32BacktestMetrics(
            gross_return=gross_return,
            transaction_cost=(
                transaction_cost
            ),
            net_return=net_return,
            trade_count=trade_count,
            turnover=float(
                turnover
            ),
            maximum_drawdown=(
                maximum_drawdown
            ),
            sharpe_like=float(
                sharpe_like
            ),
        )

    @staticmethod
    def _composite_score(
        *,
        balanced_accuracy: float,
        macro_f1: float,
        net_return: float,
        sharpe_like: float,
        maximum_drawdown: float,
        positive_fold_fraction: float,
    ) -> float:
        return_component = float(
            np.tanh(
                net_return
            )
        )

        sharpe_component = float(
            np.tanh(
                sharpe_like / 3.0
            )
        )

        drawdown_component = max(
            0.0,
            1.0
            - maximum_drawdown,
        )

        return float(
            0.20
            * balanced_accuracy
            + 0.15
            * macro_f1
            + 0.25
            * return_component
            + 0.15
            * sharpe_component
            + 0.10
            * drawdown_component
            + 0.15
            * positive_fold_fraction
        )

    def evaluate_model(
        self,
        *,
        model_name: str,
        model_template: Any,
        research: pd.DataFrame,
    ) -> V32ModelEvaluation:
        all_actual: list[int] = []
        all_predictions: list[int] = []

        fold_results = []

        total_gross_return = 0.0
        total_transaction_cost = 0.0
        total_net_return = 0.0

        total_trade_count = 0
        total_turnover = 0.0

        maximum_drawdown = 0.0

        sharpe_values = []

        ranges = self._walk_forward_ranges(
            rows=len(
                research
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
            train = research.iloc[
                train_start:train_end
            ]

            validation = research.iloc[
                validation_start:validation_end
            ]

            self._validate_target(
                train[
                    "target"
                ]
            )

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

            probabilities = (
                model.predict_proba(
                    validation[
                        FEATURE_COLUMNS
                    ]
                )
            )

            predictions = (
                self
                ._predictions_from_probabilities(
                    probabilities=(
                        probabilities
                    ),
                    classes=(
                        model.classes_
                    ),
                    threshold=(
                        self
                        ._signal_probability_threshold
                    ),
                )
            )

            actual = (
                validation[
                    "target"
                ]
                .to_numpy()
                .astype(int)
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

            backtest = (
                self
                ._simulate_positions(
                    positions=(
                        predictions
                    ),
                    forward_returns=(
                        validation[
                            "forward_return"
                        ]
                        .to_numpy()
                    ),
                )
            )

            fold_results.append(
                V32FoldMetrics(
                    fold=fold_number,
                    balanced_accuracy=(
                        balanced_accuracy
                    ),
                    macro_f1=(
                        macro_f1
                    ),
                    gross_return=(
                        backtest
                        .gross_return
                    ),
                    transaction_cost=(
                        backtest
                        .transaction_cost
                    ),
                    net_return=(
                        backtest
                        .net_return
                    ),
                    trade_count=(
                        backtest
                        .trade_count
                    ),
                    turnover=(
                        backtest
                        .turnover
                    ),
                    maximum_drawdown=(
                        backtest
                        .maximum_drawdown
                    ),
                    sharpe_like=(
                        backtest
                        .sharpe_like
                    ),
                )
            )

            all_actual.extend(
                actual.tolist()
            )

            all_predictions.extend(
                predictions.tolist()
            )

            total_gross_return += (
                backtest
                .gross_return
            )

            total_transaction_cost += (
                backtest
                .transaction_cost
            )

            total_net_return += (
                backtest
                .net_return
            )

            total_trade_count += (
                backtest
                .trade_count
            )

            total_turnover += (
                backtest
                .turnover
            )

            maximum_drawdown = max(
                maximum_drawdown,
                backtest.maximum_drawdown,
            )

            sharpe_values.append(
                backtest
                .sharpe_like
            )

        balanced_accuracy = float(
            balanced_accuracy_score(
                all_actual,
                all_predictions,
            )
        )

        macro_f1 = float(
            f1_score(
                all_actual,
                all_predictions,
                average="macro",
                zero_division=0,
            )
        )

        positive_folds = sum(
            1
            for fold
            in fold_results
            if fold.net_return > 0.0
        )

        positive_fold_fraction = (
            positive_folds
            / len(
                fold_results
            )
        )

        average_sharpe = float(
            np.mean(
                sharpe_values
            )
        )

        composite = self._composite_score(
            balanced_accuracy=(
                balanced_accuracy
            ),
            macro_f1=(
                macro_f1
            ),
            net_return=(
                total_net_return
            ),
            sharpe_like=(
                average_sharpe
            ),
            maximum_drawdown=(
                maximum_drawdown
            ),
            positive_fold_fraction=(
                positive_fold_fraction
            ),
        )

        return V32ModelEvaluation(
            model_name=model_name,
            balanced_accuracy=(
                balanced_accuracy
            ),
            macro_f1=macro_f1,
            gross_return=(
                total_gross_return
            ),
            transaction_cost=(
                total_transaction_cost
            ),
            net_return=(
                total_net_return
            ),
            trade_count=(
                total_trade_count
            ),
            turnover=(
                total_turnover
            ),
            maximum_drawdown=(
                maximum_drawdown
            ),
            sharpe_like=(
                average_sharpe
            ),
            positive_fold_fraction=(
                positive_fold_fraction
            ),
            composite_score=(
                composite
            ),
            folds=(
                fold_results
            ),
        )

    def evaluate_holdout(
        self,
        *,
        model: Any,
        holdout: pd.DataFrame,
    ) -> tuple[
        float,
        float,
        V32BacktestMetrics,
    ]:
        probabilities = (
            model.predict_proba(
                holdout[
                    FEATURE_COLUMNS
                ]
            )
        )

        predictions = (
            self
            ._predictions_from_probabilities(
                probabilities=(
                    probabilities
                ),
                classes=(
                    model.classes_
                ),
                threshold=(
                    self
                    ._signal_probability_threshold
                ),
            )
        )

        actual = (
            holdout[
                "target"
            ]
            .to_numpy()
            .astype(int)
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

        backtest = self._simulate_positions(
            positions=predictions,
            forward_returns=(
                holdout[
                    "forward_return"
                ]
                .to_numpy()
            ),
        )

        return (
            balanced_accuracy,
            macro_f1,
            backtest,
        )

    def evaluate_baseline(
        self,
        *,
        holdout: pd.DataFrame,
    ) -> tuple[
        float,
        V32BacktestMetrics,
    ]:
        momentum = (
            holdout[
                "return_5"
            ]
            .to_numpy()
        )

        predictions = np.where(
            momentum > 0.0,
            BUY,
            np.where(
                momentum < 0.0,
                SELL,
                HOLD,
            ),
        ).astype(int)

        backtest = self._simulate_positions(
            positions=predictions,
            forward_returns=(
                holdout[
                    "forward_return"
                ]
                .to_numpy()
            ),
        )

        baseline_score = (
            self._composite_score(
                balanced_accuracy=0.0,
                macro_f1=0.0,
                net_return=(
                    backtest
                    .net_return
                ),
                sharpe_like=(
                    backtest
                    .sharpe_like
                ),
                maximum_drawdown=(
                    backtest
                    .maximum_drawdown
                ),
                positive_fold_fraction=0.0,
            )
        )

        return (
            baseline_score,
            backtest,
        )

    def run_learning_cycle(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> V32LearningCycleResult:
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
                "Insufficient V3.2 learning rows. "
                f"required={self._minimum_rows}, "
                f"available={len(dataset)}."
            )

        self._validate_target(
            dataset[
                "target"
            ]
        )

        (
            research,
            holdout,
        ) = self._split_research_holdout(
            dataset=dataset
        )

        self._validate_target(
            research[
                "target"
            ]
        )

        self._validate_target(
            holdout[
                "target"
            ]
        )

        models = self.create_models()

        evaluations = []

        for (
            model_name,
            model_template,
        ) in models.items():
            evaluation = (
                self.evaluate_model(
                    model_name=model_name,
                    model_template=(
                        model_template
                    ),
                    research=research,
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

        final_candidate = clone(
            models[
                winner.model_name
            ]
        )

        final_candidate.fit(
            research[
                FEATURE_COLUMNS
            ],
            research[
                "target"
            ],
        )

        (
            holdout_balanced_accuracy,
            holdout_macro_f1,
            holdout_backtest,
        ) = self.evaluate_holdout(
            model=final_candidate,
            holdout=holdout,
        )

        (
            baseline_score,
            baseline_backtest,
        ) = self.evaluate_baseline(
            holdout=holdout
        )

        candidate_score = (
            self._composite_score(
                balanced_accuracy=(
                    holdout_balanced_accuracy
                ),
                macro_f1=(
                    holdout_macro_f1
                ),
                net_return=(
                    holdout_backtest
                    .net_return
                ),
                sharpe_like=(
                    holdout_backtest
                    .sharpe_like
                ),
                maximum_drawdown=(
                    holdout_backtest
                    .maximum_drawdown
                ),
                positive_fold_fraction=(
                    winner
                    .positive_fold_fraction
                ),
            )
        )

        champion_score = None

        if self.champion_metadata_path.exists():
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
            V32PromotionMetrics(
                balanced_accuracy=(
                    holdout_balanced_accuracy
                ),
                macro_f1=(
                    holdout_macro_f1
                ),
                net_return=(
                    holdout_backtest
                    .net_return
                ),
                trade_count=(
                    holdout_backtest
                    .trade_count
                ),
                maximum_drawdown=(
                    holdout_backtest
                    .maximum_drawdown
                ),
                sharpe_like=(
                    holdout_backtest
                    .sharpe_like
                ),
                fold_positive_fraction=(
                    winner
                    .positive_fold_fraction
                ),
                composite_score=(
                    candidate_score
                ),
            )
        )

        decision: V32PromotionDecision = (
            self._promotion_policy.evaluate(
                candidate=(
                    promotion_metrics
                ),
                baseline_score=(
                    baseline_score
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
                f"{timestamp}_"
                f"{winner.model_name}"
                ".joblib"
            )
        )

        joblib.dump(
            final_candidate,
            candidate_path,
        )

        champion_path: str | None = None

        if decision.promote:
            shutil.copyfile(
                candidate_path,
                self.champion_path,
            )

            champion_metadata = {
                "version": "3.2",
                "symbol": (
                    symbol
                    .strip()
                    .upper()
                ),
                "interval": (
                    interval
                    .strip()
                    .lower()
                ),
                "model_name": (
                    winner
                    .model_name
                ),
                "feature_columns": (
                    FEATURE_COLUMNS
                ),
                "balanced_accuracy": (
                    holdout_balanced_accuracy
                ),
                "macro_f1": (
                    holdout_macro_f1
                ),
                "gross_return": (
                    holdout_backtest
                    .gross_return
                ),
                "transaction_cost": (
                    holdout_backtest
                    .transaction_cost
                ),
                "net_return": (
                    holdout_backtest
                    .net_return
                ),
                "trade_count": (
                    holdout_backtest
                    .trade_count
                ),
                "turnover": (
                    holdout_backtest
                    .turnover
                ),
                "maximum_drawdown": (
                    holdout_backtest
                    .maximum_drawdown
                ),
                "sharpe_like": (
                    holdout_backtest
                    .sharpe_like
                ),
                "positive_fold_fraction": (
                    winner
                    .positive_fold_fraction
                ),
                "baseline_score": (
                    baseline_score
                ),
                "composite_score": (
                    candidate_score
                ),
                "promotion": (
                    asdict(
                        decision
                    )
                ),
                "promoted_at": (
                    datetime.now(UTC)
                    .isoformat()
                ),
            }

            self.champion_metadata_path.write_text(
                json.dumps(
                    champion_metadata,
                    indent=2,
                ),
                encoding="utf-8",
            )

            champion_path = str(
                self.champion_path
            )

        result = V32LearningCycleResult(
            symbol=(
                symbol.strip().upper()
            ),
            interval=(
                interval.strip().lower()
            ),
            rows_loaded=len(raw),
            rows_used=len(dataset),
            research_rows=len(
                research
            ),
            holdout_rows=len(
                holdout
            ),
            winning_model=(
                winner.model_name
            ),
            walk_forward_balanced_accuracy=(
                winner
                .balanced_accuracy
            ),
            walk_forward_macro_f1=(
                winner
                .macro_f1
            ),
            walk_forward_net_return=(
                winner
                .net_return
            ),
            holdout_balanced_accuracy=(
                holdout_balanced_accuracy
            ),
            holdout_macro_f1=(
                holdout_macro_f1
            ),
            holdout_gross_return=(
                holdout_backtest
                .gross_return
            ),
            holdout_transaction_cost=(
                holdout_backtest
                .transaction_cost
            ),
            holdout_net_return=(
                holdout_backtest
                .net_return
            ),
            holdout_trade_count=(
                holdout_backtest
                .trade_count
            ),
            holdout_turnover=(
                holdout_backtest
                .turnover
            ),
            holdout_maximum_drawdown=(
                holdout_backtest
                .maximum_drawdown
            ),
            holdout_sharpe_like=(
                holdout_backtest
                .sharpe_like
            ),
            positive_fold_fraction=(
                winner
                .positive_fold_fraction
            ),
            baseline_net_return=(
                baseline_backtest
                .net_return
            ),
            baseline_composite_score=(
                baseline_score
            ),
            candidate_composite_score=(
                candidate_score
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

        latest_path = (
            self._artifact_directory
            / "latest_learning_cycle.json"
        )

        latest_path.write_text(
            json.dumps(
                asdict(
                    result
                ),
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
    ) -> V32Signal:
        if not self.champion_path.exists():
            raise FileNotFoundError(
                "No V3.2 champion model exists."
            )

        raw = self.load_market_bars(
            symbol=symbol,
            interval=interval,
        )

        features = self.build_features(
            raw,
            include_target=False,
        )

        if features.empty:
            raise ValueError(
                "No V3.2 feature row is available."
            )

        latest = features.iloc[
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

        classes = champion.classes_

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

        result = V32Signal(
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
                asdict(
                    result
                ),
                indent=2,
            ),
            encoding="utf-8",
        )

        return result