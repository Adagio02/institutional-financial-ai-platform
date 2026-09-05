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
from sklearn.metrics import (
    balanced_accuracy_score,
    f1_score,
)
from sqlalchemy import (
    create_engine,
    text,
)

from finai.domain.learning.v33_features import (
    FEATURE_COLUMNS,
    build_features,
)
from finai.domain.learning.v33_models import (
    create_models,
)
from finai.domain.learning.v33_promotion import (
    V33PromotionDecision,
    V33PromotionMetrics,
    V33PromotionPolicy,
)
from finai.domain.learning.v33_target import (
    build_target,
)
from finai.domain.learning.v33_thresholds import (
    optimize_thresholds,
    probabilities_to_positions,
)


SELL = -1
HOLD = 0
BUY = 1


@dataclass(
    frozen=True,
    slots=True,
)
class V33BacktestMetrics:
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
class V33FoldMetrics:
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
class V33ModelEvaluation:
    model_name: str

    long_threshold: float
    short_threshold: float

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

    folds: list[V33FoldMetrics]


@dataclass(
    frozen=True,
    slots=True,
)
class V33LearningCycleResult:
    symbol: str
    interval: str

    rows_loaded: int
    rows_used: int

    research_rows: int
    holdout_rows: int
    purge_rows: int

    winning_model: str

    selected_long_threshold: float
    selected_short_threshold: float

    walk_forward_balanced_accuracy: float
    walk_forward_macro_f1: float

    walk_forward_net_return: float
    walk_forward_trade_count: int
    walk_forward_turnover: float
    walk_forward_maximum_drawdown: float

    positive_fold_fraction: float

    holdout_balanced_accuracy: float
    holdout_macro_f1: float

    holdout_gross_return: float
    holdout_transaction_cost: float
    holdout_net_return: float

    holdout_trade_count: int
    holdout_turnover: float

    holdout_maximum_drawdown: float
    holdout_sharpe_like: float

    baseline_net_return: float
    baseline_maximum_drawdown: float

    candidate_composite_score: float
    champion_score: float | None

    promoted: bool
    promotion_reason: str

    candidate_path: str
    candidate_metadata_path: str

    champion_path: str | None

    completed_at: str


@dataclass(
    frozen=True,
    slots=True,
)
class V33Signal:
    symbol: str
    interval: str

    timestamp: str

    buy_probability: float
    hold_probability: float
    sell_probability: float

    long_threshold: float
    short_threshold: float

    signal: str
    confidence: float

    model_path: str


class V33LearningService:
    def __init__(
        self,
        *,
        database_url: str,
        artifact_directory: str,
        minimum_rows: int,
        holdout_fraction: float,
        forward_horizon_bars: int,
        target_volatility_multiplier: float,
        round_trip_cost_bps: float,
        walk_forward_folds: int,
        purge_bars: int,
        long_probability_thresholds: list[float],
        short_probability_thresholds: list[float],
        minimum_balanced_accuracy: float,
        minimum_macro_f1: float,
        minimum_net_return: float,
        minimum_trades: int,
        maximum_drawdown: float,
        minimum_positive_fold_fraction: float,
        minimum_baseline_improvement: float,
        minimum_promotion_improvement: float,
        require_non_mock_data: bool,
    ) -> None:
        if minimum_rows < 1_000:
            raise ValueError(
                "minimum_rows must be at least 1000."
            )

        if not 0.10 <= holdout_fraction <= 0.40:
            raise ValueError(
                "holdout_fraction must be between "
                "0.10 and 0.40."
            )

        if forward_horizon_bars <= 0:
            raise ValueError(
                "forward_horizon_bars must "
                "be positive."
            )

        if target_volatility_multiplier < 0.0:
            raise ValueError(
                "target_volatility_multiplier "
                "cannot be negative."
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

        if purge_bars < 0:
            raise ValueError(
                "purge_bars cannot be negative."
            )

        if not long_probability_thresholds:
            raise ValueError(
                "long_probability_thresholds "
                "cannot be empty."
            )

        if not short_probability_thresholds:
            raise ValueError(
                "short_probability_thresholds "
                "cannot be empty."
            )

        for threshold in (
            long_probability_thresholds
            + short_probability_thresholds
        ):
            if not 0.0 < threshold < 1.0:
                raise ValueError(
                    "Probability thresholds must "
                    "be between zero and one."
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
        self._holdout_fraction = (
            holdout_fraction
        )

        self._forward_horizon_bars = (
            forward_horizon_bars
        )

        self._target_volatility_multiplier = (
            target_volatility_multiplier
        )

        self._round_trip_cost_bps = (
            round_trip_cost_bps
        )

        self._walk_forward_folds = (
            walk_forward_folds
        )

        self._purge_bars = max(
            purge_bars,
            forward_horizon_bars,
        )

        self._long_probability_thresholds = (
            sorted(
                set(
                    float(value)
                    for value
                    in long_probability_thresholds
                )
            )
        )

        self._short_probability_thresholds = (
            sorted(
                set(
                    float(value)
                    for value
                    in short_probability_thresholds
                )
            )
        )

        self._minimum_trades = (
            minimum_trades
        )

        self._require_non_mock_data = (
            require_non_mock_data
        )

        self._promotion_policy = (
            V33PromotionPolicy(
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
                minimum_positive_fold_fraction=(
                    minimum_positive_fold_fraction
                ),
                minimum_baseline_improvement=(
                    minimum_baseline_improvement
                ),
                minimum_champion_improvement=(
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
                "symbol cannot be blank."
            )

        if not normalized_interval:
            raise ValueError(
                "interval cannot be blank."
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
                    "symbol": (
                        normalized_symbol
                    ),
                    "interval": (
                        normalized_interval
                    ),
                },
            )

        if frame.empty:
            raise ValueError(
                "No eligible V3.3 market "
                "bars were found."
            )

        return frame

    def build_dataset(
        self,
        frame: pd.DataFrame,
        *,
        include_target: bool,
    ) -> pd.DataFrame:
        source = frame.copy()

        numeric_columns = [
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
        ]

        for column in numeric_columns:
            source[column] = pd.to_numeric(
                source[column],
                errors="coerce",
            )

        source = source.rename(
            columns={
                "open_price": "open",
                "high_price": "high",
                "low_price": "low",
                "close_price": "close",
            }
        )

        result = build_features(
            source
        )

        if include_target:
            result = build_target(
                result,
                forward_horizon_bars=(
                    self
                    ._forward_horizon_bars
                ),
                volatility_multiplier=(
                    self
                    ._target_volatility_multiplier
                ),
                round_trip_cost_bps=(
                    self
                    ._round_trip_cost_bps
                ),
            )

            required = (
                FEATURE_COLUMNS
                + [
                    "forward_return",
                    "target_edge",
                ]
            )

            result = result.dropna(
                subset=required
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
    def _validate_training_target(
        target: pd.Series,
    ) -> None:
        classes = {
            int(value)
            for value
            in target.unique()
        }

        required = {
            SELL,
            HOLD,
            BUY,
        }

        if not required.issubset(
            classes
        ):
            raise ValueError(
                "V3.3 training data must "
                "contain SELL, HOLD, and BUY."
            )

    def _split_research_holdout(
        self,
        *,
        dataset: pd.DataFrame,
    ) -> tuple[
        pd.DataFrame,
        pd.DataFrame,
    ]:
        split_index = int(
            len(dataset)
            * (
                1.0
                - self._holdout_fraction
            )
        )

        research_end = (
            split_index
            - self._purge_bars
        )

        if research_end <= 0:
            raise ValueError(
                "Research dataset is empty "
                "after holdout purge."
            )

        research = dataset.iloc[
            :research_end
        ].copy()

        holdout = dataset.iloc[
            split_index:
        ].copy()

        if research.empty:
            raise ValueError(
                "V3.3 research dataset "
                "is empty."
            )

        if holdout.empty:
            raise ValueError(
                "V3.3 holdout dataset "
                "is empty."
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
                "Insufficient rows for V3.3 "
                "walk-forward validation."
            )

        ranges: list[
            tuple[
                int,
                int,
                int,
                int,
            ]
        ] = []

        for fold in range(
            self._walk_forward_folds
        ):
            validation_start = (
                initial_train
                + fold
                * fold_size
            )

            train_end = (
                validation_start
                - self._purge_bars
            )

            if train_end <= 0:
                continue

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
                    0,
                    train_end,
                    validation_start,
                    validation_end,
                )
            )

        if not ranges:
            raise ValueError(
                "No valid V3.3 walk-forward "
                "folds were created."
            )

        return ranges

    def _evaluate_positions(
        self,
        *,
        positions: np.ndarray,
        forward_returns: np.ndarray,
    ) -> V33BacktestMetrics:
        if len(positions) != len(
            forward_returns
        ):
            raise ValueError(
                "positions and forward_returns "
                "must have equal length."
            )

        if len(positions) == 0:
            return V33BacktestMetrics(
                gross_return=0.0,
                transaction_cost=0.0,
                net_return=0.0,
                trade_count=0,
                turnover=0.0,
                maximum_drawdown=0.0,
                sharpe_like=0.0,
            )

        positions = positions.astype(
            float
        )

        forward_returns = (
            forward_returns.astype(
                float
            )
        )

        previous_positions = np.concatenate(
            (
                np.array(
                    [
                        0.0,
                    ]
                ),
                positions[:-1],
            )
        )

        changes = np.abs(
            positions
            - previous_positions
        )

        one_way_cost = (
            self._round_trip_cost_bps
            / 20_000.0
        )

        gross_series = (
            positions
            * forward_returns
        )

        cost_series = (
            changes
            * one_way_cost
        )

        net_series = (
            gross_series
            - cost_series
        )

        gross_equity = np.cumprod(
            1.0
            + gross_series
        )

        net_equity = np.cumprod(
            1.0
            + net_series
        )

        gross_return = float(
            gross_equity[-1]
            - 1.0
        )

        net_return = float(
            net_equity[-1]
            - 1.0
        )

        transaction_cost = float(
            np.sum(
                cost_series
            )
        )

        running_peak = (
            np.maximum.accumulate(
                net_equity
            )
        )

        drawdown = (
            net_equity
            / running_peak
            - 1.0
        )

        maximum_drawdown = float(
            abs(
                np.min(
                    drawdown
                )
            )
        )

        standard_deviation = float(
            np.std(
                net_series
            )
        )

        if standard_deviation > 0.0:
            sharpe_like = float(
                np.mean(
                    net_series
                )
                / standard_deviation
                * np.sqrt(
                    len(
                        net_series
                    )
                )
            )

        else:
            sharpe_like = 0.0

        trade_count = int(
            np.count_nonzero(
                changes > 0.0
            )
        )

        turnover = float(
            np.sum(
                changes
            )
        )

        return V33BacktestMetrics(
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
            turnover=turnover,
            maximum_drawdown=(
                maximum_drawdown
            ),
            sharpe_like=(
                sharpe_like
            ),
        )

    @staticmethod
    def _classification_metrics(
        *,
        actual: np.ndarray,
        positions: np.ndarray,
    ) -> tuple[
        float,
        float,
    ]:
        balanced_accuracy = float(
            balanced_accuracy_score(
                actual,
                positions.astype(
                    int
                ),
            )
        )

        macro_f1 = float(
            f1_score(
                actual,
                positions.astype(
                    int
                ),
                average="macro",
                zero_division=0,
            )
        )

        return (
            balanced_accuracy,
            macro_f1,
        )

    @staticmethod
    def _research_composite_score(
        *,
        balanced_accuracy: float,
        macro_f1: float,
        net_return: float,
        positive_fold_fraction: float,
        maximum_drawdown: float,
        turnover: float,
    ) -> float:
        return float(
            0.30
            * balanced_accuracy
            + 0.20
            * macro_f1
            + 2.00
            * net_return
            + 0.10
            * positive_fold_fraction
            - 0.75
            * maximum_drawdown
            - 0.00001
            * turnover
        )

    @staticmethod
    def _holdout_composite_score(
        *,
        balanced_accuracy: float,
        macro_f1: float,
        net_return: float,
        maximum_drawdown: float,
        turnover: float,
    ) -> float:
        return float(
            0.30
            * balanced_accuracy
            + 0.20
            * macro_f1
            + 2.00
            * net_return
            - 0.75
            * maximum_drawdown
            - 0.00001
            * turnover
        )

    def evaluate_model(
        self,
        *,
        model_name: str,
        model_template: Any,
        research: pd.DataFrame,
    ) -> V33ModelEvaluation:
        fold_payloads: list[
            dict[str, Any]
        ] = []

        all_probabilities = []
        all_actual = []
        all_forward_returns = []

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

            self._validate_training_target(
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

            actual = (
                validation[
                    "target"
                ]
                .to_numpy()
                .astype(int)
            )

            forward_returns = (
                validation[
                    "forward_return"
                ]
                .to_numpy()
                .astype(float)
            )

            fold_payloads.append(
                {
                    "fold": (
                        fold_number
                    ),
                    "probabilities": (
                        probabilities
                    ),
                    "classes": (
                        model.classes_
                        .copy()
                    ),
                    "actual": actual,
                    "forward_returns": (
                        forward_returns
                    ),
                }
            )

            all_probabilities.append(
                probabilities
            )

            all_actual.append(
                actual
            )

            all_forward_returns.append(
                forward_returns
            )

        if not fold_payloads:
            raise RuntimeError(
                "V3.3 model evaluation "
                "produced no folds."
            )

        classes = fold_payloads[
            0
        ][
            "classes"
        ]

        for payload in fold_payloads:
            if not np.array_equal(
                payload[
                    "classes"
                ],
                classes,
            ):
                raise RuntimeError(
                    "Model class ordering changed "
                    "between walk-forward folds."
                )

        probabilities = np.concatenate(
            all_probabilities,
            axis=0,
        )

        actual = np.concatenate(
            all_actual,
            axis=0,
        )

        forward_returns = np.concatenate(
            all_forward_returns,
            axis=0,
        )

        threshold_result = (
            optimize_thresholds(
                probabilities=(
                    probabilities
                ),
                classes=classes,
                forward_returns=(
                    forward_returns
                ),
                long_thresholds=(
                    self
                    ._long_probability_thresholds
                ),
                short_thresholds=(
                    self
                    ._short_probability_thresholds
                ),
                round_trip_cost_bps=(
                    self
                    ._round_trip_cost_bps
                ),
                minimum_trades=(
                    self._minimum_trades
                ),
            )
        )

        long_threshold = (
            threshold_result
            .long_threshold
        )

        short_threshold = (
            threshold_result
            .short_threshold
        )

        all_positions = (
            probabilities_to_positions(
                probabilities=(
                    probabilities
                ),
                classes=classes,
                long_threshold=(
                    long_threshold
                ),
                short_threshold=(
                    short_threshold
                ),
            )
        )

        (
            balanced_accuracy,
            macro_f1,
        ) = self._classification_metrics(
            actual=actual,
            positions=all_positions,
        )

        overall_backtest = (
            self._evaluate_positions(
                positions=(
                    all_positions
                ),
                forward_returns=(
                    forward_returns
                ),
            )
        )

        fold_results = []

        for payload in fold_payloads:
            positions = (
                probabilities_to_positions(
                    probabilities=(
                        payload[
                            "probabilities"
                        ]
                    ),
                    classes=(
                        payload[
                            "classes"
                        ]
                    ),
                    long_threshold=(
                        long_threshold
                    ),
                    short_threshold=(
                        short_threshold
                    ),
                )
            )

            (
                fold_balanced_accuracy,
                fold_macro_f1,
            ) = self._classification_metrics(
                actual=(
                    payload[
                        "actual"
                    ]
                ),
                positions=positions,
            )

            fold_backtest = (
                self._evaluate_positions(
                    positions=positions,
                    forward_returns=(
                        payload[
                            "forward_returns"
                        ]
                    ),
                )
            )

            fold_results.append(
                V33FoldMetrics(
                    fold=(
                        payload[
                            "fold"
                        ]
                    ),
                    balanced_accuracy=(
                        fold_balanced_accuracy
                    ),
                    macro_f1=(
                        fold_macro_f1
                    ),
                    gross_return=(
                        fold_backtest
                        .gross_return
                    ),
                    transaction_cost=(
                        fold_backtest
                        .transaction_cost
                    ),
                    net_return=(
                        fold_backtest
                        .net_return
                    ),
                    trade_count=(
                        fold_backtest
                        .trade_count
                    ),
                    turnover=(
                        fold_backtest
                        .turnover
                    ),
                    maximum_drawdown=(
                        fold_backtest
                        .maximum_drawdown
                    ),
                    sharpe_like=(
                        fold_backtest
                        .sharpe_like
                    ),
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

        composite_score = (
            self
            ._research_composite_score(
                balanced_accuracy=(
                    balanced_accuracy
                ),
                macro_f1=macro_f1,
                net_return=(
                    overall_backtest
                    .net_return
                ),
                positive_fold_fraction=(
                    positive_fold_fraction
                ),
                maximum_drawdown=(
                    overall_backtest
                    .maximum_drawdown
                ),
                turnover=(
                    overall_backtest
                    .turnover
                ),
            )
        )

        return V33ModelEvaluation(
            model_name=model_name,
            long_threshold=(
                long_threshold
            ),
            short_threshold=(
                short_threshold
            ),
            balanced_accuracy=(
                balanced_accuracy
            ),
            macro_f1=(
                macro_f1
            ),
            gross_return=(
                overall_backtest
                .gross_return
            ),
            transaction_cost=(
                overall_backtest
                .transaction_cost
            ),
            net_return=(
                overall_backtest
                .net_return
            ),
            trade_count=(
                overall_backtest
                .trade_count
            ),
            turnover=(
                overall_backtest
                .turnover
            ),
            maximum_drawdown=(
                overall_backtest
                .maximum_drawdown
            ),
            sharpe_like=(
                overall_backtest
                .sharpe_like
            ),
            positive_fold_fraction=(
                positive_fold_fraction
            ),
            composite_score=(
                composite_score
            ),
            folds=fold_results,
        )

    def _evaluate_frozen_candidate(
        self,
        *,
        model: Any,
        holdout: pd.DataFrame,
        long_threshold: float,
        short_threshold: float,
    ) -> tuple[
        float,
        float,
        V33BacktestMetrics,
    ]:
        probabilities = (
            model.predict_proba(
                holdout[
                    FEATURE_COLUMNS
                ]
            )
        )

        positions = (
            probabilities_to_positions(
                probabilities=(
                    probabilities
                ),
                classes=(
                    model.classes_
                ),
                long_threshold=(
                    long_threshold
                ),
                short_threshold=(
                    short_threshold
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

        (
            balanced_accuracy,
            macro_f1,
        ) = self._classification_metrics(
            actual=actual,
            positions=positions,
        )

        backtest = (
            self._evaluate_positions(
                positions=positions,
                forward_returns=(
                    holdout[
                        "forward_return"
                    ]
                    .to_numpy()
                    .astype(float)
                ),
            )
        )

        return (
            balanced_accuracy,
            macro_f1,
            backtest,
        )

    def _evaluate_baseline(
        self,
        *,
        holdout: pd.DataFrame,
    ) -> V33BacktestMetrics:
        momentum = (
            holdout[
                "return_5"
            ]
            .to_numpy()
            .astype(float)
        )

        positions = np.where(
            momentum > 0.0,
            BUY,
            np.where(
                momentum < 0.0,
                SELL,
                HOLD,
            ),
        ).astype(float)

        return self._evaluate_positions(
            positions=positions,
            forward_returns=(
                holdout[
                    "forward_return"
                ]
                .to_numpy()
                .astype(float)
            ),
        )

    def _load_champion_score(
        self,
    ) -> float | None:
        if not (
            self
            .champion_metadata_path
            .exists()
        ):
            return None

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

        if raw_score is None:
            return None

        return float(
            raw_score
        )

    def run_learning_cycle(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> V33LearningCycleResult:
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

        raw = self.load_market_bars(
            symbol=(
                normalized_symbol
            ),
            interval=(
                normalized_interval
            ),
        )

        dataset = self.build_dataset(
            raw,
            include_target=True,
        )

        if len(dataset) < self._minimum_rows:
            raise ValueError(
                "Insufficient V3.3 learning rows. "
                f"required={self._minimum_rows}, "
                f"available={len(dataset)}."
            )

        self._validate_training_target(
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

        self._validate_training_target(
            research[
                "target"
            ]
        )

        models = create_models()

        evaluations = []

        for (
            model_name,
            model_template,
        ) in models.items():
            evaluation = self.evaluate_model(
                model_name=model_name,
                model_template=(
                    model_template
                ),
                research=research,
            )

            evaluations.append(
                evaluation
            )

        if not evaluations:
            raise RuntimeError(
                "V3.3 produced no candidate "
                "model evaluations."
            )

        evaluations.sort(
            key=lambda item: (
                item.composite_score
            ),
            reverse=True,
        )

        winner = evaluations[
            0
        ]

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
        ) = self._evaluate_frozen_candidate(
            model=final_candidate,
            holdout=holdout,
            long_threshold=(
                winner
                .long_threshold
            ),
            short_threshold=(
                winner
                .short_threshold
            ),
        )

        baseline_backtest = (
            self._evaluate_baseline(
                holdout=holdout
            )
        )

        candidate_score = (
            self
            ._holdout_composite_score(
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
                maximum_drawdown=(
                    holdout_backtest
                    .maximum_drawdown
                ),
                turnover=(
                    holdout_backtest
                    .turnover
                ),
            )
        )

        champion_score = (
            self._load_champion_score()
        )

        promotion_metrics = (
            V33PromotionMetrics(
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
                positive_fold_fraction=(
                    winner
                    .positive_fold_fraction
                ),
                baseline_net_return=(
                    baseline_backtest
                    .net_return
                ),
                composite_score=(
                    candidate_score
                ),
            )
        )

        decision: V33PromotionDecision = (
            self
            ._promotion_policy
            .evaluate(
                metrics=(
                    promotion_metrics
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

        candidate_metadata_path = (
            self._artifact_directory
            / (
                "candidate_"
                f"{timestamp}_"
                f"{winner.model_name}"
                ".json"
            )
        )

        joblib.dump(
            final_candidate,
            candidate_path,
        )

        candidate_metadata = {
            "version": "3.3",
            "symbol": (
                normalized_symbol
            ),
            "interval": (
                normalized_interval
            ),
            "model_name": (
                winner.model_name
            ),
            "feature_columns": (
                FEATURE_COLUMNS
            ),
            "forward_horizon_bars": (
                self
                ._forward_horizon_bars
            ),
            "purge_bars": (
                self._purge_bars
            ),
            "long_threshold": (
                winner
                .long_threshold
            ),
            "short_threshold": (
                winner
                .short_threshold
            ),
            "round_trip_cost_bps": (
                self
                ._round_trip_cost_bps
            ),
            "walk_forward": (
                asdict(
                    winner
                )
            ),
            "holdout": {
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
            },
            "baseline": (
                asdict(
                    baseline_backtest
                )
            ),
            "composite_score": (
                candidate_score
            ),
            "promotion": (
                asdict(
                    decision
                )
            ),
            "created_at": (
                datetime.now(UTC)
                .isoformat()
            ),
        }

        candidate_metadata_path.write_text(
            json.dumps(
                candidate_metadata,
                indent=2,
            ),
            encoding="utf-8",
        )

        champion_path: str | None = None

        if decision.promote:
            shutil.copyfile(
                candidate_path,
                self.champion_path,
            )

            champion_metadata = (
                candidate_metadata.copy()
            )

            champion_metadata[
                "promoted_at"
            ] = (
                datetime.now(UTC)
                .isoformat()
            )

            champion_metadata[
                "model_path"
            ] = str(
                self.champion_path
            )

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

        result = V33LearningCycleResult(
            symbol=normalized_symbol,
            interval=(
                normalized_interval
            ),
            rows_loaded=len(
                raw
            ),
            rows_used=len(
                dataset
            ),
            research_rows=len(
                research
            ),
            holdout_rows=len(
                holdout
            ),
            purge_rows=(
                self._purge_bars
            ),
            winning_model=(
                winner.model_name
            ),
            selected_long_threshold=(
                winner
                .long_threshold
            ),
            selected_short_threshold=(
                winner
                .short_threshold
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
            walk_forward_trade_count=(
                winner
                .trade_count
            ),
            walk_forward_turnover=(
                winner
                .turnover
            ),
            walk_forward_maximum_drawdown=(
                winner
                .maximum_drawdown
            ),
            positive_fold_fraction=(
                winner
                .positive_fold_fraction
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
            baseline_net_return=(
                baseline_backtest
                .net_return
            ),
            baseline_maximum_drawdown=(
                baseline_backtest
                .maximum_drawdown
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
            candidate_metadata_path=str(
                candidate_metadata_path
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
    ) -> V33Signal:
        if not self.champion_path.exists():
            raise FileNotFoundError(
                "No V3.3 champion model exists."
            )

        if not (
            self
            .champion_metadata_path
            .exists()
        ):
            raise FileNotFoundError(
                "V3.3 champion metadata "
                "does not exist."
            )

        metadata = json.loads(
            self
            .champion_metadata_path
            .read_text(
                encoding="utf-8"
            )
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

        raw = self.load_market_bars(
            symbol=symbol,
            interval=interval,
        )

        features = self.build_dataset(
            raw,
            include_target=False,
        )

        if features.empty:
            raise ValueError(
                "No V3.3 feature row "
                "is available."
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
            )
        )

        positions = (
            probabilities_to_positions(
                probabilities=(
                    probabilities
                ),
                classes=(
                    champion.classes_
                ),
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
            for (
                label,
                probability,
            )
            in zip(
                champion.classes_,
                probabilities[
                    0
                ],
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

        if position == BUY:
            signal = "buy"
            confidence = (
                buy_probability
            )

        elif position == SELL:
            signal = "sell"
            confidence = (
                sell_probability
            )

        else:
            signal = "hold"
            confidence = max(
                probability_by_class.values()
            )

        result = V33Signal(
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
                latest.iloc[
                    0
                ][
                    "timestamp"
                ]
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
            long_threshold=(
                long_threshold
            ),
            short_threshold=(
                short_threshold
            ),
            signal=signal,
            confidence=(
                confidence
            ),
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