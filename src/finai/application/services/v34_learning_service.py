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
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone

from finai.application.services.v33_learning_service import (
    BUY,
    HOLD,
    SELL,
    V33BacktestMetrics,
    V33LearningService,
)
from finai.domain.learning.v33_features import (
    FEATURE_COLUMNS,
)
from finai.domain.learning.v33_models import (
    create_models,
)
from finai.domain.learning.v33_thresholds import (
    optimize_thresholds,
    probabilities_to_positions,
)
from finai.domain.learning.v34_promotion import (
    V34PromotionDecision,
    V34PromotionMetrics,
    V34PromotionPolicy,
)
from finai.domain.learning.v34_regimes import (
    assign_regimes,
    calculate_regime_boundaries,
)


@dataclass(
    frozen=True,
    slots=True,
)
class V34FoldMetrics:
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
class V34ModelEvaluation:
    model_name: str

    long_threshold: float
    short_threshold: float

    long_threshold_std: float
    short_threshold_std: float
    threshold_std: float

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

    folds: list[V34FoldMetrics]


@dataclass(
    frozen=True,
    slots=True,
)
class V34LearningCycleResult:
    symbol: str
    interval: str

    rows_loaded: int
    rows_used: int

    research_rows: int
    holdout_rows: int

    winning_model: str

    selected_long_threshold: float
    selected_short_threshold: float

    threshold_std: float

    walk_forward_balanced_accuracy: float
    walk_forward_macro_f1: float

    walk_forward_net_return: float

    positive_fold_fraction: float
    worst_fold_return: float

    holdout_balanced_accuracy: float
    holdout_macro_f1: float

    holdout_net_return: float
    holdout_trade_count: int

    holdout_maximum_drawdown: float
    holdout_sharpe_like: float

    baseline_net_return: float

    worst_regime_return: float

    candidate_composite_score: float
    champion_score: float | None

    promoted: bool
    promotion_reason: str

    candidate_path: str
    candidate_metadata_path: str

    champion_path: str | None

    completed_at: str


class V34LearningService(
    V33LearningService
):
    def __init__(
        self,
        *,
        inner_calibration_fraction: float,
        threshold_search_minimum_trades: int,
        minimum_worst_fold_return: float,
        maximum_threshold_std: float,
        minimum_regime_return: float,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            **kwargs
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

        if (
            threshold_search_minimum_trades
            < 1
        ):
            raise ValueError(
                "threshold_search_minimum_trades "
                "must be positive."
            )

        self._inner_calibration_fraction = (
            inner_calibration_fraction
        )

        self._threshold_search_minimum_trades = (
            threshold_search_minimum_trades
        )

        self._v34_promotion_policy = (
            V34PromotionPolicy(
                minimum_balanced_accuracy=(
                    kwargs[
                        "minimum_balanced_accuracy"
                    ]
                ),
                minimum_macro_f1=(
                    kwargs[
                        "minimum_macro_f1"
                    ]
                ),
                minimum_net_return=(
                    kwargs[
                        "minimum_net_return"
                    ]
                ),
                minimum_trades=(
                    kwargs[
                        "minimum_trades"
                    ]
                ),
                maximum_drawdown=(
                    kwargs[
                        "maximum_drawdown"
                    ]
                ),
                minimum_positive_fold_fraction=(
                    kwargs[
                        "minimum_positive_fold_fraction"
                    ]
                ),
                minimum_worst_fold_return=(
                    minimum_worst_fold_return
                ),
                maximum_threshold_std=(
                    maximum_threshold_std
                ),
                minimum_regime_return=(
                    minimum_regime_return
                ),
                minimum_baseline_improvement=(
                    kwargs[
                        "minimum_baseline_improvement"
                    ]
                ),
                minimum_champion_improvement=(
                    kwargs[
                        "minimum_promotion_improvement"
                    ]
                ),
            )
        )

    def build_dataset(
        self,
        frame: pd.DataFrame,
        *,
        include_target: bool,
    ) -> pd.DataFrame:
        result = super().build_dataset(
            frame,
            include_target=(
                include_target
            ),
        )

        if "close" not in result.columns:
            raise ValueError(
                "V3.4 dataset contains no close price."
            )

        result[
            "execution_return"
        ] = (
            result[
                "close"
            ]
            .astype(float)
            .pct_change()
            .shift(-1)
        )

        if include_target:
            result = result.dropna(
                subset=[
                    "execution_return",
                ]
            )

        return result.reset_index(
            drop=True
        )

    def _inner_split(
        self,
        *,
        outer_train: pd.DataFrame,
    ) -> tuple[
        pd.DataFrame,
        pd.DataFrame,
    ]:
        calibration_rows = max(
            1,
            int(
                len(
                    outer_train
                )
                * self
                ._inner_calibration_fraction
            ),
        )

        calibration_start = (
            len(
                outer_train
            )
            - calibration_rows
        )

        inner_train_end = (
            calibration_start
            - self._purge_bars
        )

        if inner_train_end <= 0:
            raise ValueError(
                "Outer training fold is too small "
                "for nested calibration."
            )

        inner_train = outer_train.iloc[
            :inner_train_end
        ].copy()

        calibration = outer_train.iloc[
            calibration_start:
        ].copy()

        return (
            inner_train,
            calibration,
        )

    def evaluate_model(
        self,
        *,
        model_name: str,
        model_template: Any,
        research: pd.DataFrame,
    ) -> V34ModelEvaluation:
        fold_results = []

        all_actual = []
        all_positions = []
        all_execution_returns = []

        long_thresholds = []
        short_thresholds = []

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
            outer_train = research.iloc[
                train_start:train_end
            ].copy()

            outer_validation = (
                research.iloc[
                    validation_start:
                    validation_end
                ].copy()
            )

            (
                inner_train,
                calibration,
            ) = self._inner_split(
                outer_train=(
                    outer_train
                )
            )

            self._validate_training_target(
                inner_train[
                    "target"
                ]
            )

            threshold_model = clone(
                model_template
            )

            threshold_model.fit(
                inner_train[
                    FEATURE_COLUMNS
                ],
                inner_train[
                    "target"
                ],
            )

            calibration_probabilities = (
                threshold_model.predict_proba(
                    calibration[
                        FEATURE_COLUMNS
                    ]
                )
            )

            threshold_result = (
                optimize_thresholds(
                    probabilities=(
                        calibration_probabilities
                    ),
                    classes=(
                        threshold_model.classes_
                    ),
                    forward_returns=(
                        calibration[
                            "execution_return"
                        ]
                        .to_numpy()
                        .astype(float)
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
                        self
                        ._threshold_search_minimum_trades
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

            long_thresholds.append(
                long_threshold
            )

            short_thresholds.append(
                short_threshold
            )

            outer_model = clone(
                model_template
            )

            outer_model.fit(
                outer_train[
                    FEATURE_COLUMNS
                ],
                outer_train[
                    "target"
                ],
            )

            probabilities = (
                outer_model.predict_proba(
                    outer_validation[
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
                        outer_model.classes_
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
                outer_validation[
                    "target"
                ]
                .to_numpy()
                .astype(int)
            )

            execution_returns = (
                outer_validation[
                    "execution_return"
                ]
                .to_numpy()
                .astype(float)
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
                        execution_returns
                    ),
                )
            )

            fold_results.append(
                V34FoldMetrics(
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
                    macro_f1=(
                        macro_f1
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

            all_actual.append(
                actual
            )

            all_positions.append(
                positions
            )

            all_execution_returns.append(
                execution_returns
            )

        if not fold_results:
            raise RuntimeError(
                "V3.4 produced no fold results."
            )

        actual = np.concatenate(
            all_actual
        )

        positions = np.concatenate(
            all_positions
        )

        execution_returns = np.concatenate(
            all_execution_returns
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
                    execution_returns
                ),
            )
        )

        positive_fold_fraction = (
            sum(
                1
                for fold
                in fold_results
                if fold.net_return > 0.0
            )
            / len(
                fold_results
            )
        )

        worst_fold_return = min(
            fold.net_return
            for fold
            in fold_results
        )

        long_threshold_std = float(
            np.std(
                long_thresholds
            )
        )

        short_threshold_std = float(
            np.std(
                short_thresholds
            )
        )

        threshold_std = max(
            long_threshold_std,
            short_threshold_std,
        )

        final_long_threshold = float(
            np.median(
                long_thresholds
            )
        )

        final_short_threshold = float(
            np.median(
                short_thresholds
            )
        )

        composite_score = (
            0.25
            * balanced_accuracy
            + 0.15
            * macro_f1
            + 1.50
            * backtest.net_return
            + 0.15
            * positive_fold_fraction
            - 0.75
            * backtest.maximum_drawdown
            - 0.50
            * abs(
                min(
                    worst_fold_return,
                    0.0,
                )
            )
            - 0.25
            * threshold_std
            - 0.00001
            * backtest.turnover
        )

        return V34ModelEvaluation(
            model_name=model_name,
            long_threshold=(
                final_long_threshold
            ),
            short_threshold=(
                final_short_threshold
            ),
            long_threshold_std=(
                long_threshold_std
            ),
            short_threshold_std=(
                short_threshold_std
            ),
            threshold_std=(
                threshold_std
            ),
            balanced_accuracy=(
                balanced_accuracy
            ),
            macro_f1=(
                macro_f1
            ),
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
                backtest.maximum_drawdown
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
            composite_score=float(
                composite_score
            ),
            folds=fold_results,
        )

    def _evaluate_holdout(
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
        np.ndarray,
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
                probabilities=probabilities,
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
                        "execution_return"
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
            positions,
        )

    def _regime_returns(
        self,
        *,
        research: pd.DataFrame,
        holdout: pd.DataFrame,
        positions: np.ndarray,
    ) -> dict[str, float]:
        boundaries = (
            calculate_regime_boundaries(
                research
            )
        )

        regimes = assign_regimes(
            holdout,
            boundaries=(
                boundaries
            ),
        )

        returns = (
            holdout[
                "execution_return"
            ]
            .to_numpy()
            .astype(float)
        )

        results = {}

        unique_regimes = sorted(
            set(
                regimes.tolist()
            )
        )

        for regime in unique_regimes:
            mask = (
                regimes
                .to_numpy()
                == regime
            )

            if not np.any(
                mask
            ):
                continue

            backtest = (
                self._evaluate_positions(
                    positions=(
                        positions[
                            mask
                        ]
                    ),
                    forward_returns=(
                        returns[
                            mask
                        ]
                    ),
                )
            )

            results[
                regime
            ] = float(
                backtest.net_return
            )

        return results

    def run_learning_cycle(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> V34LearningCycleResult:
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
            symbol=normalized_symbol,
            interval=normalized_interval,
        )

        dataset = self.build_dataset(
            raw,
            include_target=True,
        )

        if (
            len(
                dataset
            )
            < self._minimum_rows
        ):
            raise ValueError(
                "Insufficient V3.4 learning rows. "
                f"required={self._minimum_rows}, "
                f"available={len(dataset)}."
            )

        (
            research,
            holdout,
        ) = self._split_research_holdout(
            dataset=dataset
        )

        models = create_models()

        evaluations = []

        for (
            model_name,
            model_template,
        ) in models.items():
            evaluations.append(
                self.evaluate_model(
                    model_name=model_name,
                    model_template=(
                        model_template
                    ),
                    research=research,
                )
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

        candidate = clone(
            models[
                winner.model_name
            ]
        )

        candidate.fit(
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
            holdout_positions,
        ) = self._evaluate_holdout(
            model=candidate,
            holdout=holdout,
            long_threshold=(
                winner.long_threshold
            ),
            short_threshold=(
                winner.short_threshold
            ),
        )

        baseline = (
            self._evaluate_positions(
                positions=np.where(
                    holdout[
                        "return_5"
                    ]
                    .to_numpy()
                    > 0.0,
                    BUY,
                    np.where(
                        holdout[
                            "return_5"
                        ]
                        .to_numpy()
                        < 0.0,
                        SELL,
                        HOLD,
                    ),
                ),
                forward_returns=(
                    holdout[
                        "execution_return"
                    ]
                    .to_numpy()
                ),
            )
        )

        regime_returns = (
            self._regime_returns(
                research=research,
                holdout=holdout,
                positions=(
                    holdout_positions
                ),
            )
        )

        if regime_returns:
            worst_regime_return = min(
                regime_returns.values()
            )

        else:
            worst_regime_return = 0.0

        candidate_score = float(
            0.25
            * holdout_balanced_accuracy
            + 0.15
            * holdout_macro_f1
            + 1.50
            * holdout_backtest.net_return
            - 0.75
            * holdout_backtest.maximum_drawdown
            - 0.25
            * winner.threshold_std
            - 0.00001
            * holdout_backtest.turnover
        )

        champion_score = (
            self._load_champion_score()
        )

        metrics = V34PromotionMetrics(
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
            worst_fold_return=(
                winner
                .worst_fold_return
            ),
            threshold_std=(
                winner
                .threshold_std
            ),
            worst_regime_return=(
                worst_regime_return
            ),
            baseline_net_return=(
                baseline.net_return
            ),
            composite_score=(
                candidate_score
            ),
        )

        decision: V34PromotionDecision = (
            self
            ._v34_promotion_policy
            .evaluate(
                metrics=metrics,
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

        metadata_path = (
            self._artifact_directory
            / (
                "candidate_"
                f"{timestamp}_"
                f"{winner.model_name}"
                ".json"
            )
        )

        joblib.dump(
            candidate,
            candidate_path,
        )

        metadata = {
            "version": "3.4",
            "symbol": normalized_symbol,
            "interval": normalized_interval,
            "model_name": (
                winner.model_name
            ),
            "feature_columns": (
                FEATURE_COLUMNS
            ),
            "long_threshold": (
                winner.long_threshold
            ),
            "short_threshold": (
                winner.short_threshold
            ),
            "threshold_std": (
                winner.threshold_std
            ),
            "regime_returns": (
                regime_returns
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
                "sharpe_like": (
                    holdout_backtest
                    .sharpe_like
                ),
            },
            "baseline_net_return": (
                baseline.net_return
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

        metadata_path.write_text(
            json.dumps(
                metadata,
                indent=2,
            ),
            encoding="utf-8",
        )

        champion_path = None

        if decision.promote:
            shutil.copyfile(
                candidate_path,
                self.champion_path,
            )

            champion_metadata = (
                metadata.copy()
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

        result = V34LearningCycleResult(
            symbol=normalized_symbol,
            interval=normalized_interval,
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
            selected_long_threshold=(
                winner.long_threshold
            ),
            selected_short_threshold=(
                winner.short_threshold
            ),
            threshold_std=(
                winner.threshold_std
            ),
            walk_forward_balanced_accuracy=(
                winner.balanced_accuracy
            ),
            walk_forward_macro_f1=(
                winner.macro_f1
            ),
            walk_forward_net_return=(
                winner.net_return
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
            holdout_sharpe_like=(
                holdout_backtest
                .sharpe_like
            ),
            baseline_net_return=(
                baseline.net_return
            ),
            worst_regime_return=(
                worst_regime_return
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
                metadata_path
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

        (
            self._artifact_directory
            / (
                "evaluation_"
                f"{timestamp}.json"
            )
        ).write_text(
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