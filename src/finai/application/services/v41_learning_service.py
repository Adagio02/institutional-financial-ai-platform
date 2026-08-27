from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from datetime import (
    UTC,
    datetime,
)
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone

from finai.application.services.v38_learning_service import (
    V38BacktestMetrics,
    V38FoldMetrics,
    V38LearningCycleResult,
    V38ModelEvaluation,
)
from finai.application.services.v40_learning_service import (
    V40LearningService,
)
from finai.domain.learning.v41_features import (
    V41_FEATURE_COLUMNS,
    build_v41_features,
)
from finai.domain.learning.v41_models import (
    create_v41_models,
)


class V41LearningService(
    V40LearningService
):
    VERSION = "4.1"

    LEARNING_ARCHITECTURE = (
        "cost_aware_regime_ensemble"
    )

    def __init__(
        self,
        *,
        shadow_directory: str,
        round_trip_cost_bps: float,
        **kwargs: Any,
    ) -> None:
        if round_trip_cost_bps < 0.0:
            raise ValueError(
                "round_trip_cost_bps cannot "
                "be negative."
            )

        super().__init__(
            shadow_directory=(
                shadow_directory
            ),
            round_trip_cost_bps=(
                round_trip_cost_bps
            ),
            **kwargs,
        )

        self._v41_round_trip_cost_bps = float(
            round_trip_cost_bps
        )

    @property
    def feature_columns(
        self,
    ) -> list[str]:
        return list(
            V41_FEATURE_COLUMNS
        )

    def create_model_templates(
        self,
    ) -> dict[str, Any]:
        return create_v41_models(
            minimum_regime_rows=(
                self._minimum_regime_rows
            )
        )
    def build_dataset(
        self,
        *,
        symbol: str,
        interval: str,
        include_target: bool,
    ) -> tuple[pd.DataFrame, int]:
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

        target_bars = self.load_market_bars(
            symbol=normalized_symbol,
            interval=normalized_interval,
        )

        spy_bars = self.load_market_bars(
            symbol="SPY",
            interval=normalized_interval,
        )

        qqq_bars = self.load_market_bars(
            symbol="QQQ",
            interval=normalized_interval,
        )

        rows_loaded = len(
            target_bars
        )

        if target_bars.empty:
            raise RuntimeError(
                f"No market bars exist for "
                f"{normalized_symbol}."
            )

        if spy_bars.empty:
            raise RuntimeError(
                "No SPY context bars exist."
            )

        if qqq_bars.empty:
            raise RuntimeError(
                "No QQQ context bars exist."
            )

        dataset = build_v41_features(
            target_bars=target_bars,
            spy_bars=spy_bars,
            qqq_bars=qqq_bars,
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
            rows_loaded,
        )

    def simulate(
        self,
        *,
        positions: np.ndarray,
        forward_returns: np.ndarray,
    ) -> V38BacktestMetrics:
        normalized_positions = np.asarray(
            positions,
            dtype=int,
        )

        normalized_returns = np.asarray(
            forward_returns,
            dtype=float,
        )

        if (
            len(normalized_positions)
            != len(normalized_returns)
        ):
            raise ValueError(
                "Position and return row counts "
                "do not match."
            )

        if len(normalized_positions) == 0:
            return V38BacktestMetrics(
                gross_return=0.0,
                transaction_cost=0.0,
                net_return=0.0,
                trade_count=0,
                turnover=0.0,
                maximum_drawdown=0.0,
                sharpe_like=0.0,
            )

        strategy_returns = (
            normalized_positions
            * normalized_returns
        )

        previous_positions = np.concatenate(
            (
                np.asarray(
                    [0],
                    dtype=int,
                ),
                normalized_positions[:-1],
            )
        )

        position_changes = np.abs(
            normalized_positions
            - previous_positions
        ).astype(float)

        turnover = float(
            np.sum(
                position_changes
            )
        )

        trade_count = int(
            np.sum(
                position_changes > 0.0
            )
        )

        cost_rate = (
            self._v41_round_trip_cost_bps
            / 10_000.0
        )

        transaction_costs = (
            position_changes
            * cost_rate
        )

        net_strategy_returns = (
            strategy_returns
            - transaction_costs
        )

        gross_equity = np.cumprod(
            1.0
            + strategy_returns
        )

        net_equity = np.cumprod(
            1.0
            + net_strategy_returns
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
                transaction_costs
            )
        )

        running_peak = np.maximum.accumulate(
            net_equity
        )

        drawdowns = (
            1.0
            - (
                net_equity
                / np.where(
                    running_peak == 0.0,
                    1.0,
                    running_peak,
                )
            )
        )

        maximum_drawdown = float(
            np.max(
                drawdowns
            )
        )

        return_std = float(
            np.std(
                net_strategy_returns
            )
        )

        if return_std > 0.0:
            sharpe_like = float(
                np.mean(
                    net_strategy_returns
                )
                / return_std
                * np.sqrt(
                    len(
                        net_strategy_returns
                    )
                )
            )
        else:
            sharpe_like = 0.0

        return V38BacktestMetrics(
            gross_return=gross_return,
            transaction_cost=(
                transaction_cost
            ),
            net_return=net_return,
            trade_count=trade_count,
            turnover=turnover,
            maximum_drawdown=(
                maximum_drawdown
            ),
            sharpe_like=sharpe_like,
        )

    def evaluate_model(
        self,
        *,
        model_name: str,
        model_template: Any,
        research: pd.DataFrame,
    ) -> V38ModelEvaluation:
        minimum_training_rows = max(
            500,
            self._minimum_regime_rows,
        )

        available_rows = len(
            research
        )

        if (
            available_rows
            <= minimum_training_rows
        ):
            raise RuntimeError(
                "Insufficient V4.1 research "
                "rows for walk-forward "
                "evaluation."
            )

        validation_rows = max(
            1,
            available_rows
            // (
                self._walk_forward_folds
                + 1
            ),
        )

        folds: list[
            V38FoldMetrics
        ] = []

        all_actual: list[
            np.ndarray
        ] = []

        all_positions: list[
            np.ndarray
        ] = []

        all_returns: list[
            np.ndarray
        ] = []

        long_thresholds: list[
            float
        ] = []

        short_thresholds: list[
            float
        ] = []

        for fold_number in range(
            1,
            self._walk_forward_folds
            + 1,
        ):
            validation_end = (
                available_rows
                - (
                    self._walk_forward_folds
                    - fold_number
                )
                * validation_rows
            )

            validation_start = (
                validation_end
                - validation_rows
            )

            training_end = (
                validation_start
                - self._purge_rows
            )

            if (
                training_end
                <= minimum_training_rows
            ):
                continue

            train = research.iloc[
                :training_end
            ].copy()

            validation = research.iloc[
                validation_start:
                validation_end
            ].copy()

            calibration_rows = max(
                100,
                int(
                    len(train)
                    * self
                    ._inner_calibration_fraction
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
                    V41_FEATURE_COLUMNS
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
                    V41_FEATURE_COLUMNS
                ],
                train["target"],
            )

            probabilities = (
                model.predict_proba(
                    validation[
                        V41_FEATURE_COLUMNS
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
                        backtest
                        .maximum_drawdown
                    ),
                    sharpe_like=(
                        backtest.sharpe_like
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

        if not folds:
            raise RuntimeError(
                "V4.1 produced no valid "
                "walk-forward folds."
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
            macro_f1=(
                macro_f1
            ),
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
                    V41_FEATURE_COLUMNS
                ]
            )
        )

        best: tuple[
            float,
            float,
            V38BacktestMetrics,
        ] | None = None

        best_score = float(
            "-inf"
        )

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
                        long_threshold=float(
                            long_threshold
                        ),
                        short_threshold=float(
                            short_threshold
                        ),
                    )
                )

                backtest = self.simulate(
                    positions=positions,
                    forward_returns=(
                        calibration[
                            "forward_return"
                        ]
                        .to_numpy(
                            dtype=float
                        )
                    ),
                )

                if (
                    backtest.trade_count
                    < self._minimum_trades
                ):
                    continue

                score = (
                    backtest.net_return
                    - (
                        backtest
                        .maximum_drawdown
                        * 0.50
                    )
                    + (
                        backtest
                        .sharpe_like
                        * 0.02
                    )
                )

                if score > best_score:
                    best_score = score

                    best = (
                        float(
                            long_threshold
                        ),
                        float(
                            short_threshold
                        ),
                        backtest,
                    )

        if best is None:
            raise RuntimeError(
                "No V4.1 threshold configuration "
                "satisfied minimum_trades."
            )

        return best

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
        probabilities = (
            model.predict_proba(
                holdout[
                    V41_FEATURE_COLUMNS
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
            symbol=(
                normalized_symbol
            ),
            interval=(
                normalized_interval
            ),
            include_target=True,
        )

        if (
            len(dataset)
            < self._minimum_rows
        ):
            raise ValueError(
                "Insufficient synchronized V4.1 "
                "learning rows. "
                f"required={self._minimum_rows}, "
                f"available={len(dataset)}."
            )

        holdout_rows = max(
            1,
            int(
                len(dataset)
                * self._holdout_fraction
            ),
        )

        research_end = (
            len(dataset)
            - holdout_rows
            - self._purge_rows
        )

        if research_end <= 0:
            raise RuntimeError(
                "V4.1 research split is empty."
            )

        research = dataset.iloc[
            :research_end
        ].copy()

        holdout = dataset.iloc[
            -holdout_rows:
        ].copy()

        model_templates = (
            self.create_model_templates()
        )

        evaluations = []

        for (
            model_name,
            template,
        ) in model_templates.items():
            evaluation = (
                self.evaluate_model(
                    model_name=(
                        model_name
                    ),
                    model_template=(
                        template
                    ),
                    research=(
                        research
                    ),
                )
            )

            evaluations.append(
                evaluation
            )

        if not evaluations:
            raise RuntimeError(
                "V4.1 produced no model "
                "evaluations."
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
                V41_FEATURE_COLUMNS
            ],
            research["target"],
        )

        (
            holdout_balanced_accuracy,
            holdout_macro_f1,
            holdout_backtest,
        ) = self.evaluate_holdout(
            model=(
                winning_model
            ),
            holdout=(
                holdout
            ),
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
            historically_qualified,
            qualification_reason,
            candidate_score,
        ) = self._promotion_decision(
            winner=winner,
            holdout_balanced_accuracy=(
                holdout_balanced_accuracy
            ),
            holdout_macro_f1=(
                holdout_macro_f1
            ),
            holdout=(
                holdout_backtest
            ),
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
                V41_FEATURE_COLUMNS
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
            "version": "4.1",
            "learning_architecture": (
                self.LEARNING_ARCHITECTURE
            ),
            "symbol": (
                normalized_symbol
            ),
            "interval": (
                normalized_interval
            ),
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
            "feature_columns": list(
                V41_FEATURE_COLUMNS
            ),
            "feature_count": len(
                V41_FEATURE_COLUMNS
            ),
            "target": {
                "forward_horizon_bars": (
                    self
                    ._forward_horizon_bars
                ),
                "minimum_edge_bps": (
                    self
                    ._target_minimum_edge_bps
                ),
                "round_trip_cost_bps": (
                    self
                    ._v41_round_trip_cost_bps
                ),
                "cost_aware": True,
            },
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
                "sharpe_like": (
                    holdout_backtest
                    .sharpe_like
                ),
            },
            "composite_score": (
                candidate_score
            ),
            "historical_qualified": (
                historically_qualified
            ),
            "historical_reason": (
                qualification_reason
            ),
            "shadow_required": True,
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

        shadow_candidate_path = None
        shadow_metadata_path = None

        if historically_qualified:
            self._shadow_directory.mkdir(
                parents=True,
                exist_ok=True,
            )

            shadow_candidate = (
                self._shadow_directory
                / "shadow_candidate.joblib"
            )

            shadow_metadata = (
                self._shadow_directory
                / "shadow_candidate.json"
            )

            shutil.copyfile(
                candidate_path,
                shadow_candidate,
            )

            shadow_payload = dict(
                candidate_metadata
            )

            shadow_payload[
                "model_path"
            ] = str(
                shadow_candidate
            )

            shadow_payload[
                "shadow_started_at"
            ] = (
                datetime.now(UTC)
                .isoformat()
            )

            shadow_payload[
                "shadow_observations"
            ] = 0

            shadow_metadata.write_text(
                json.dumps(
                    shadow_payload,
                    indent=2,
                ),
                encoding="utf-8",
            )

            shadow_candidate_path = str(
                shadow_candidate
            )

            shadow_metadata_path = str(
                shadow_metadata
            )

        result = V38LearningCycleResult(
            symbol=normalized_symbol,
            interval=normalized_interval,
            context_symbols=[
                "SPY",
                "QQQ",
            ],
            rows_loaded=(
                rows_loaded
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
            promoted=False,
            promotion_reason=(
                (
                    "Historically qualified; "
                    "shadow validation required."
                )
                if historically_qualified
                else qualification_reason
            ),
            candidate_path=str(
                candidate_path
            ),
            candidate_metadata_path=str(
                candidate_metadata_path
            ),
            champion_path=None,
            completed_at=(
                datetime.now(UTC)
                .isoformat()
            ),
        )

        latest_payload = {
            **asdict(
                result
            ),
            "version": "4.1",
            "historical_qualified": (
                historically_qualified
            ),
            "historical_reason": (
                qualification_reason
            ),
            "shadow_required": True,
            "shadow_candidate_path": (
                shadow_candidate_path
            ),
            "shadow_metadata_path": (
                shadow_metadata_path
            ),
        }

        (
            self._artifact_directory
            / "latest_learning_cycle.json"
        ).write_text(
            json.dumps(
                latest_payload,
                indent=2,
            ),
            encoding="utf-8",
        )

        return result