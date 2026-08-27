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

from finai.domain.learning.v38_features import (
    V38_FEATURE_COLUMNS,
    build_v38_features,
)
from finai.domain.learning.v38_models import (
    create_v38_models,
)


BUY = 1
HOLD = 0
SELL = -1


@dataclass(
    frozen=True,
    slots=True,
)
class V38BacktestMetrics:
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
class V38FoldMetrics:
    fold: int

    long_threshold: float
    short_threshold: float

    balanced_accuracy: float
    macro_f1: float

    net_return: float

    trade_count: int
    turnover: float

    maximum_drawdown: float
    sharpe_like: float


@dataclass(
    frozen=True,
    slots=True,
)
class V38ModelEvaluation:
    model_name: str

    long_threshold: float
    short_threshold: float

    balanced_accuracy: float
    macro_f1: float

    net_return: float

    trade_count: int
    turnover: float

    maximum_drawdown: float
    sharpe_like: float

    positive_fold_fraction: float
    worst_fold_return: float

    composite_score: float

    folds: list[V38FoldMetrics]


@dataclass(
    frozen=True,
    slots=True,
)
class V38LearningCycleResult:
    symbol: str
    interval: str

    context_symbols: list[str]

    rows_loaded: int
    rows_used: int

    research_rows: int
    holdout_rows: int

    winning_model: str

    selected_long_threshold: float
    selected_short_threshold: float

    walk_forward_balanced_accuracy: float
    walk_forward_macro_f1: float

    walk_forward_net_return: float
    walk_forward_trade_count: int

    positive_fold_fraction: float
    worst_fold_return: float

    holdout_balanced_accuracy: float
    holdout_macro_f1: float

    holdout_net_return: float
    holdout_trade_count: int
    holdout_maximum_drawdown: float

    candidate_composite_score: float

    champion_score: float | None

    promoted: bool
    promotion_reason: str

    candidate_path: str
    candidate_metadata_path: str

    champion_path: str | None

    completed_at: str


class V38LearningService:
    def __init__(
        self,
        *,
        database_url: str,
        artifact_directory: str,
        minimum_rows: int,
        forward_horizon_bars: int,
        target_minimum_edge_bps: float,
        holdout_fraction: float,
        walk_forward_folds: int,
        purge_rows: int,
        round_trip_cost_bps: float,
        long_probability_thresholds: list[float],
        short_probability_thresholds: list[float],
        inner_calibration_fraction: float,
        minimum_balanced_accuracy: float,
        minimum_macro_f1: float,
        minimum_net_return: float,
        minimum_positive_fold_fraction: float,
        minimum_trades: int,
        maximum_holdout_drawdown: float,
        minimum_promotion_improvement: float,
        require_non_mock_data: bool = True,
    ) -> None:
        if minimum_rows < 1000:
            raise ValueError(
                "minimum_rows must be at least 1000."
            )

        if forward_horizon_bars <= 0:
            raise ValueError(
                "forward_horizon_bars must be positive."
            )

        if not 0.05 <= holdout_fraction <= 0.40:
            raise ValueError(
                "holdout_fraction must be "
                "between 0.05 and 0.40."
            )

        if walk_forward_folds < 2:
            raise ValueError(
                "walk_forward_folds must be at least 2."
            )

        if purge_rows < 0:
            raise ValueError(
                "purge_rows cannot be negative."
            )

        if round_trip_cost_bps < 0.0:
            raise ValueError(
                "round_trip_cost_bps cannot be negative."
            )

        if not (
            0.10
            <= inner_calibration_fraction
            <= 0.40
        ):
            raise ValueError(
                "inner_calibration_fraction must "
                "be between 0.10 and 0.40."
            )

        if not long_probability_thresholds:
            raise ValueError(
                "Long thresholds cannot be empty."
            )

        if not short_probability_thresholds:
            raise ValueError(
                "Short thresholds cannot be empty."
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

        self._holdout_fraction = (
            holdout_fraction
        )

        self._walk_forward_folds = (
            walk_forward_folds
        )

        self._purge_rows = purge_rows

        self._round_trip_cost_bps = (
            round_trip_cost_bps
        )

        self._long_probability_thresholds = (
            long_probability_thresholds
        )

        self._short_probability_thresholds = (
            short_probability_thresholds
        )

        self._inner_calibration_fraction = (
            inner_calibration_fraction
        )

        self._minimum_balanced_accuracy = (
            minimum_balanced_accuracy
        )

        self._minimum_macro_f1 = (
            minimum_macro_f1
        )

        self._minimum_net_return = (
            minimum_net_return
        )

        self._minimum_positive_fold_fraction = (
            minimum_positive_fold_fraction
        )

        self._minimum_trades = minimum_trades

        self._maximum_holdout_drawdown = (
            maximum_holdout_drawdown
        )

        self._minimum_promotion_improvement = (
            minimum_promotion_improvement
        )

        self._require_non_mock_data = (
            require_non_mock_data
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
                "No eligible market bars were found. "
                f"symbol={normalized_symbol}, "
                f"interval={normalized_interval}."
            )

        frame["timestamp"] = pd.to_datetime(
            frame["timestamp"],
            utc=True,
        )

        return (
            frame
            .sort_values("timestamp")
            .drop_duplicates(
                subset=["timestamp"],
                keep="last",
            )
            .reset_index(drop=True)
        )

    def build_dataset(
        self,
        *,
        symbol: str,
        interval: str,
        include_target: bool,
    ) -> tuple[
        pd.DataFrame,
        int,
    ]:
        target = self.load_market_bars(
            symbol=symbol,
            interval=interval,
        )

        spy = self.load_market_bars(
            symbol="SPY",
            interval=interval,
        )

        qqq = self.load_market_bars(
            symbol="QQQ",
            interval=interval,
        )

        dataset = build_v38_features(
            target_bars=target,
            spy_bars=spy,
            qqq_bars=qqq,
            forward_horizon_bars=(
                self._forward_horizon_bars
            ),
            minimum_edge_bps=(
                self._target_minimum_edge_bps
            ),
            include_target=include_target,
        )

        return (
            dataset,
            len(target),
        )

    @staticmethod
    def _probability_map(
        *,
        probabilities: np.ndarray,
        classes: np.ndarray,
    ) -> dict[int, np.ndarray]:
        return {
            int(label): probabilities[
                :,
                index,
            ]
            for index, label
            in enumerate(
                classes
            )
        }

    @classmethod
    def positions_from_probabilities(
        cls,
        *,
        probabilities: np.ndarray,
        classes: np.ndarray,
        long_threshold: float,
        short_threshold: float,
    ) -> np.ndarray:
        probability_map = (
            cls._probability_map(
                probabilities=probabilities,
                classes=classes,
            )
        )

        long_probability = (
            probability_map.get(
                BUY,
                np.zeros(
                    len(probabilities)
                ),
            )
        )

        short_probability = (
            probability_map.get(
                SELL,
                np.zeros(
                    len(probabilities)
                ),
            )
        )

        positions = np.zeros(
            len(probabilities),
            dtype=int,
        )

        long_mask = (
            (long_probability >= long_threshold)
            & (
                long_probability
                > short_probability
            )
        )

        short_mask = (
            (short_probability >= short_threshold)
            & (
                short_probability
                > long_probability
            )
        )

        positions[
            long_mask
        ] = BUY

        positions[
            short_mask
        ] = SELL

        return positions

    def simulate(
        self,
        *,
        positions: np.ndarray,
        forward_returns: np.ndarray,
    ) -> V38BacktestMetrics:
        positions = np.asarray(
            positions,
            dtype=int,
        )

        forward_returns = np.asarray(
            forward_returns,
            dtype=float,
        )

        gross_returns = (
            positions
            * forward_returns
        )

        previous_positions = np.concatenate(
            [
                np.asarray(
                    [0],
                    dtype=int,
                ),
                positions[:-1],
            ]
        )

        turnover_array = np.abs(
            positions
            - previous_positions
        ).astype(float)

        cost_per_turn = (
            self._round_trip_cost_bps
            / 10_000.0
        )

        costs = (
            turnover_array
            * cost_per_turn
        )

        net_returns = (
            gross_returns
            - costs
        )

        gross_return = float(
            np.sum(
                gross_returns
            )
        )

        transaction_cost = float(
            np.sum(
                costs
            )
        )

        net_return = float(
            np.sum(
                net_returns
            )
        )

        equity = np.cumprod(
            1.0
            + net_returns
        )

        if len(
            equity
        ) == 0:
            maximum_drawdown = 0.0

        else:
            running_maximum = (
                np.maximum.accumulate(
                    equity
                )
            )

            drawdown = (
                equity
                / running_maximum
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
                net_returns
            )
        )

        if standard_deviation <= 0.0:
            sharpe_like = 0.0

        else:
            sharpe_like = float(
                np.mean(
                    net_returns
                )
                / standard_deviation
                * np.sqrt(
                    252.0
                    * 390.0
                    / max(
                        1,
                        self
                        ._forward_horizon_bars
                    )
                )
            )

        trade_count = int(
            np.sum(
                (
                    positions != 0
                )
                & (
                    positions
                    != previous_positions
                )
            )
        )

        return V38BacktestMetrics(
            gross_return=gross_return,
            transaction_cost=(
                transaction_cost
            ),
            net_return=net_return,
            trade_count=trade_count,
            turnover=float(
                np.sum(
                    turnover_array
                )
            ),
            maximum_drawdown=(
                maximum_drawdown
            ),
            sharpe_like=(
                sharpe_like
            ),
        )

    def _optimize_thresholds(
        self,
        *,
        model: Any,
        calibration: pd.DataFrame,
    ) -> tuple[
        float,
        float,
        V38BacktestMetrics,
    ]:
        probabilities = (
            model.predict_proba(
                calibration[
                    V38_FEATURE_COLUMNS
                ]
            )
        )

        forward_returns = (
            calibration[
                "forward_return"
            ]
            .to_numpy(
                dtype=float
            )
        )

        best_score = (
            -float(
                "inf"
            )
        )

        best_result = None

        for long_threshold in (
            self
            ._long_probability_thresholds
        ):
            for short_threshold in (
                self
                ._short_probability_thresholds
            ):
                positions = (
                    self
                    .positions_from_probabilities(
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

                backtest = self.simulate(
                    positions=positions,
                    forward_returns=(
                        forward_returns
                    ),
                )

                if (
                    backtest.trade_count
                    < 5
                ):
                    continue

                score = (
                    backtest.net_return
                    - (
                        0.50
                        * backtest
                        .maximum_drawdown
                    )
                )

                if score > best_score:
                    best_score = score

                    best_result = (
                        float(
                            long_threshold
                        ),
                        float(
                            short_threshold
                        ),
                        backtest,
                    )

        if best_result is None:
            return (
                0.60,
                0.60,
                V38BacktestMetrics(
                    gross_return=0.0,
                    transaction_cost=0.0,
                    net_return=0.0,
                    trade_count=0,
                    turnover=0.0,
                    maximum_drawdown=0.0,
                    sharpe_like=0.0,
                ),
            )

        return best_result

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
        minimum_training = int(
            rows
            * 0.40
        )

        remaining = (
            rows
            - minimum_training
        )

        fold_size = (
            remaining
            // self
            ._walk_forward_folds
        )

        if fold_size <= 0:
            raise RuntimeError(
                "Insufficient rows for "
                "walk-forward evaluation."
            )

        ranges = []

        for fold in range(
            self._walk_forward_folds
        ):
            train_start = 0

            train_end = (
                minimum_training
                + fold
                * fold_size
            )

            validation_start = (
                train_end
                + self._purge_rows
            )

            if (
                fold
                == self
                ._walk_forward_folds
                - 1
            ):
                validation_end = rows

            else:
                validation_end = (
                    validation_start
                    + fold_size
                )

            if (
                validation_start
                >= validation_end
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

        if len(
            ranges
        ) < 2:
            raise RuntimeError(
                "Insufficient valid "
                "walk-forward folds."
            )

        return ranges

    @staticmethod
    def _classification_metrics(
        *,
        actual: np.ndarray,
        predicted: np.ndarray,
    ) -> tuple[
        float,
        float,
    ]:
        return (
            float(
                balanced_accuracy_score(
                    actual,
                    predicted,
                )
            ),
            float(
                f1_score(
                    actual,
                    predicted,
                    average="macro",
                    zero_division=0,
                )
            ),
        )

    @staticmethod
    def _composite_score(
        *,
        balanced_accuracy: float,
        macro_f1: float,
        net_return: float,
        maximum_drawdown: float,
        positive_fold_fraction: float,
    ) -> float:
        return float(
            (
                balanced_accuracy
                * 0.30
            )
            + (
                macro_f1
                * 0.20
            )
            + (
                net_return
                * 0.30
            )
            + (
                positive_fold_fraction
                * 0.20
            )
            - (
                maximum_drawdown
                * 0.30
            )
        )

    def evaluate_model(
        self,
        *,
        model_name: str,
        model_template: Any,
        research: pd.DataFrame,
    ) -> V38ModelEvaluation:
        folds = []

        all_actual = []
        all_positions = []
        all_returns = []

        long_thresholds = []
        short_thresholds = []

        for fold_number, (
            train_start,
            train_end,
            validation_start,
            validation_end,
        ) in enumerate(
            self._walk_forward_ranges(
                rows=len(
                    research
                )
            ),
            start=1,
        ):
            train = research.iloc[
                train_start:train_end
            ].copy()

            validation = research.iloc[
                validation_start:validation_end
            ].copy()

            calibration_rows = max(
                100,
                int(
                    len(train)
                    * (
                        self
                        ._inner_calibration_fraction
                    )
                ),
            )

            if (
                calibration_rows
                >= len(train)
            ):
                calibration_rows = max(
                    1,
                    len(train)
                    // 5,
                )

            training = train.iloc[
                :-calibration_rows
            ]

            calibration = train.iloc[
                -calibration_rows:
            ]

            model = clone(
                model_template
            )

            model.fit(
                training[
                    V38_FEATURE_COLUMNS
                ],
                training["target"],
            )

            (
                long_threshold,
                short_threshold,
                _,
            ) = self._optimize_thresholds(
                model=model,
                calibration=calibration,
            )

            model.fit(
                train[
                    V38_FEATURE_COLUMNS
                ],
                train["target"],
            )

            probabilities = (
                model.predict_proba(
                    validation[
                        V38_FEATURE_COLUMNS
                    ]
                )
            )

            positions = (
                self
                .positions_from_probabilities(
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
                validation[
                    "target"
                ]
                .to_numpy(
                    dtype=int
                )
            )

            (
                balanced_accuracy,
                macro_f1,
            ) = (
                self
                ._classification_metrics(
                    actual=actual,
                    predicted=positions,
                )
            )

            backtest = self.simulate(
                positions=positions,
                forward_returns=(
                    validation[
                        "forward_return"
                    ]
                    .to_numpy(
                        dtype=float
                    )
                ),
            )

            folds.append(
                V38FoldMetrics(
                    fold=fold_number,
                    long_threshold=(
                        long_threshold
                    ),
                    short_threshold=(
                        short_threshold
                    ),
                    balanced_accuracy=(
                        balanced_accuracy
                    ),
                    macro_f1=macro_f1,
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

            all_actual.append(
                actual
            )

            all_positions.append(
                positions
            )

            all_returns.append(
                validation[
                    "forward_return"
                ]
                .to_numpy(
                    dtype=float
                )
            )

            long_thresholds.append(
                long_threshold
            )

            short_thresholds.append(
                short_threshold
            )

        actual = np.concatenate(
            all_actual
        )

        positions = np.concatenate(
            all_positions
        )

        forward_returns = np.concatenate(
            all_returns
        )

        (
            balanced_accuracy,
            macro_f1,
        ) = self._classification_metrics(
            actual=actual,
            predicted=positions,
        )

        backtest = self.simulate(
            positions=positions,
            forward_returns=(
                forward_returns
            ),
        )

        positive_fold_fraction = float(
            np.mean(
                [
                    fold.net_return
                    > 0.0
                    for fold
                    in folds
                ]
            )
        )

        worst_fold_return = float(
            min(
                fold.net_return
                for fold
                in folds
            )
        )

        composite = self._composite_score(
            balanced_accuracy=(
                balanced_accuracy
            ),
            macro_f1=macro_f1,
            net_return=(
                backtest.net_return
            ),
            maximum_drawdown=(
                backtest
                .maximum_drawdown
            ),
            positive_fold_fraction=(
                positive_fold_fraction
            ),
        )

        return V38ModelEvaluation(
            model_name=model_name,
            long_threshold=float(
                np.median(
                    long_thresholds
                )
            ),
            short_threshold=float(
                np.median(
                    short_thresholds
                )
            ),
            balanced_accuracy=(
                balanced_accuracy
            ),
            macro_f1=macro_f1,
            net_return=(
                backtest.net_return
            ),
            trade_count=(
                backtest.trade_count
            ),
            turnover=(
                backtest.turnover
            ),
            maximum_drawdown=(
                backtest
                .maximum_drawdown
            ),
            sharpe_like=(
                backtest.sharpe_like
            ),
            positive_fold_fraction=(
                positive_fold_fraction
            ),
            worst_fold_return=(
                worst_fold_return
            ),
            composite_score=(
                composite
            ),
            folds=folds,
        )

    def evaluate_holdout(
        self,
        *,
        model: Any,
        holdout: pd.DataFrame,
        long_threshold: float,
        short_threshold: float,
    ) -> tuple[
        float,
        float,
        V38BacktestMetrics,
    ]:
        probabilities = model.predict_proba(
            holdout[
                V38_FEATURE_COLUMNS
            ]
        )

        positions = (
            self
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

        actual = (
            holdout[
                "target"
            ]
            .to_numpy(
                dtype=int
            )
        )

        (
            balanced_accuracy,
            macro_f1,
        ) = self._classification_metrics(
            actual=actual,
            predicted=positions,
        )

        backtest = self.simulate(
            positions=positions,
            forward_returns=(
                holdout[
                    "forward_return"
                ]
                .to_numpy(
                    dtype=float
                )
            ),
        )

        return (
            balanced_accuracy,
            macro_f1,
            backtest,
        )

    def _promotion_decision(
        self,
        *,
        winner: V38ModelEvaluation,
        holdout_balanced_accuracy: float,
        holdout_macro_f1: float,
        holdout: V38BacktestMetrics,
        champion_score: float | None,
    ) -> tuple[
        bool,
        str,
        float,
    ]:
        candidate_score = (
            self._composite_score(
                balanced_accuracy=(
                    holdout_balanced_accuracy
                ),
                macro_f1=(
                    holdout_macro_f1
                ),
                net_return=(
                    holdout.net_return
                ),
                maximum_drawdown=(
                    holdout
                    .maximum_drawdown
                ),
                positive_fold_fraction=(
                    winner
                    .positive_fold_fraction
                ),
            )
        )

        if (
            holdout_balanced_accuracy
            < (
                self
                ._minimum_balanced_accuracy
            )
        ):
            return (
                False,
                (
                    "Holdout balanced accuracy "
                    "does not satisfy minimum."
                ),
                candidate_score,
            )

        if (
            holdout_macro_f1
            < self._minimum_macro_f1
        ):
            return (
                False,
                (
                    "Holdout macro F1 does not "
                    "satisfy minimum."
                ),
                candidate_score,
            )

        if (
            holdout.net_return
            <= self._minimum_net_return
        ):
            return (
                False,
                (
                    "Holdout net return does not "
                    "satisfy minimum."
                ),
                candidate_score,
            )

        if (
            holdout.trade_count
            < self._minimum_trades
        ):
            return (
                False,
                (
                    "Holdout trade count does not "
                    "satisfy minimum."
                ),
                candidate_score,
            )

        if (
            holdout.maximum_drawdown
            > (
                self
                ._maximum_holdout_drawdown
            )
        ):
            return (
                False,
                (
                    "Holdout maximum drawdown "
                    "exceeds limit."
                ),
                candidate_score,
            )

        if (
            winner.positive_fold_fraction
            < (
                self
                ._minimum_positive_fold_fraction
            )
        ):
            return (
                False,
                (
                    "Positive walk-forward fold "
                    "fraction is below minimum."
                ),
                candidate_score,
            )

        if winner.net_return <= 0.0:
            return (
                False,
                (
                    "Walk-forward net return "
                    "is not positive."
                ),
                candidate_score,
            )

        if winner.worst_fold_return < -0.05:
            return (
                False,
                (
                    "Worst walk-forward fold "
                    "loss is excessive."
                ),
                candidate_score,
            )

        if champion_score is None:
            return (
                True,
                (
                    "Candidate passed all V3.8 "
                    "research and holdout gates."
                ),
                candidate_score,
            )

        improvement = (
            candidate_score
            - champion_score
        )

        if (
            improvement
            < (
                self
                ._minimum_promotion_improvement
            )
        ):
            return (
                False,
                (
                    "Candidate did not outperform "
                    "the current V3.8 champion by "
                    "the required margin."
                ),
                candidate_score,
            )

        return (
            True,
            (
                "Candidate passed all gates and "
                "outperformed the V3.8 champion."
            ),
            candidate_score,
        )

    def run_learning_cycle(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> V38LearningCycleResult:
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

        (
            dataset,
            rows_loaded,
        ) = self.build_dataset(
            symbol=normalized_symbol,
            interval=normalized_interval,
            include_target=True,
        )

        if len(dataset) < self._minimum_rows:
            raise ValueError(
                "Insufficient synchronized V3.8 "
                "learning rows. "
                f"required={self._minimum_rows}, "
                f"available={len(dataset)}."
            )

        holdout_rows = max(
            1,
            int(
                len(dataset)
                * self
                ._holdout_fraction
            ),
        )

        research_end = (
            len(dataset)
            - holdout_rows
            - self._purge_rows
        )

        if research_end <= 0:
            raise RuntimeError(
                "V3.8 research split is empty."
            )

        research = dataset.iloc[
            :research_end
        ].copy()

        holdout = dataset.iloc[
            -holdout_rows:
        ].copy()

        evaluations = []

        model_templates = (
            create_v38_models()
        )

        for model_name, template in (
            model_templates.items()
        ):
            evaluation = (
                self.evaluate_model(
                    model_name=(
                        model_name
                    ),
                    model_template=(
                        template
                    ),
                    research=research,
                )
            )

            evaluations.append(
                evaluation
            )

        winner = max(
            evaluations,
            key=lambda value: (
                value.composite_score
            ),
        )

        winning_model = clone(
            model_templates[
                winner.model_name
            ]
        )

        winning_model.fit(
            research[
                V38_FEATURE_COLUMNS
            ],
            research["target"],
        )

        (
            holdout_balanced_accuracy,
            holdout_macro_f1,
            holdout_backtest,
        ) = self.evaluate_holdout(
            model=winning_model,
            holdout=holdout,
            long_threshold=(
                winner.long_threshold
            ),
            short_threshold=(
                winner.short_threshold
            ),
        )

        champion_score = None

        if (
            self
            .champion_metadata_path
            .exists()
        ):
            try:
                champion_metadata = (
                    json.loads(
                        self
                        .champion_metadata_path
                        .read_text(
                            encoding="utf-8"
                        )
                    )
                )

                champion_score = float(
                    champion_metadata[
                        "composite_score"
                    ]
                )

            except (
                KeyError,
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ):
                champion_score = None

        (
            promote,
            promotion_reason,
            candidate_score,
        ) = self._promotion_decision(
            winner=winner,
            holdout_balanced_accuracy=(
                holdout_balanced_accuracy
            ),
            holdout_macro_f1=(
                holdout_macro_f1
            ),
            holdout=holdout_backtest,
            champion_score=(
                champion_score
            ),
        )

        final_model = clone(
            model_templates[
                winner.model_name
            ]
        )

        final_model.fit(
            dataset[
                V38_FEATURE_COLUMNS
            ],
            dataset["target"],
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
            candidate_path
            .with_suffix(
                ".json"
            )
        )

        joblib.dump(
            final_model,
            candidate_path,
        )

        candidate_metadata = {
            "version": "3.8",
            "symbol": normalized_symbol,
            "interval": normalized_interval,
            "context_symbols": [
                "SPY",
                "QQQ",
            ],
            "model_name": (
                winner.model_name
            ),
            "model_path": str(
                candidate_path
            ),
            "feature_columns": (
                V38_FEATURE_COLUMNS
            ),
            "long_threshold": (
                winner.long_threshold
            ),
            "short_threshold": (
                winner.short_threshold
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
                "net_return": (
                    holdout_backtest
                    .net_return
                ),
                "trade_count": (
                    holdout_backtest
                    .trade_count
                ),
                "maximum_drawdown": (
                    holdout_backtest
                    .maximum_drawdown
                ),
            },
            "composite_score": (
                candidate_score
            ),
            "promoted": promote,
            "promotion_reason": (
                promotion_reason
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

        champion_path = None

        if promote:
            shutil.copyfile(
                candidate_path,
                self.champion_path,
            )

            champion_metadata = dict(
                candidate_metadata
            )

            champion_metadata[
                "model_path"
            ] = str(
                self.champion_path
            )

            champion_metadata[
                "promoted_at"
            ] = (
                datetime.now(UTC)
                .isoformat()
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

        result = V38LearningCycleResult(
            symbol=normalized_symbol,
            interval=normalized_interval,
            context_symbols=[
                "SPY",
                "QQQ",
            ],
            rows_loaded=rows_loaded,
            rows_used=len(
                dataset
            ),
            research_rows=len(
                research
            ),
            holdout_rows=len(
                holdout
            ),
            winning_model=(
                winner.model_name
            ),
            selected_long_threshold=(
                winner.long_threshold
            ),
            selected_short_threshold=(
                winner.short_threshold
            ),
            walk_forward_balanced_accuracy=(
                winner
                .balanced_accuracy
            ),
            walk_forward_macro_f1=(
                winner.macro_f1
            ),
            walk_forward_net_return=(
                winner.net_return
            ),
            walk_forward_trade_count=(
                winner.trade_count
            ),
            positive_fold_fraction=(
                winner
                .positive_fold_fraction
            ),
            worst_fold_return=(
                winner
                .worst_fold_return
            ),
            holdout_balanced_accuracy=(
                holdout_balanced_accuracy
            ),
            holdout_macro_f1=(
                holdout_macro_f1
            ),
            holdout_net_return=(
                holdout_backtest
                .net_return
            ),
            holdout_trade_count=(
                holdout_backtest
                .trade_count
            ),
            holdout_maximum_drawdown=(
                holdout_backtest
                .maximum_drawdown
            ),
            candidate_composite_score=(
                candidate_score
            ),
            champion_score=(
                champion_score
            ),
            promoted=promote,
            promotion_reason=(
                promotion_reason
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

        (
            self._artifact_directory
            / "latest_learning_cycle.json"
        ).write_text(
            json.dumps(
                asdict(
                    result
                ),
                indent=2,
            ),
            encoding="utf-8",
        )

        return result