from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    balanced_accuracy_score,
    f1_score,
    precision_score,
)

from finai.application.services.v453_learning_service import (
    V453LearningService,
)
from finai.domain.learning.v44_research import (
    split_discovery_locked_final,
    write_json,
)
from finai.domain.learning.v46_events import (
    EVENT_FAMILIES,
    META_FEATURE_COLUMNS,
    apply_event_family,
)
from finai.domain.learning.v46_models import (
    MODEL_CONFIGS,
    create_meta_model,
)
from finai.domain.learning.v46_research import (
    HORIZONS,
    META_THRESHOLD_GRID,
)


class V46LearningService(V453LearningService):
    VERSION = "4.6"
    LEARNING_ARCHITECTURE = (
        "conditional_event_meta_label_"
        "discovery_only"
    )

    def __init__(
        self,
        *,
        v46_artifact_directory: str = "artifacts/v46",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._v46_artifact_directory = Path(
            v46_artifact_directory
        )
        self._v46_artifact_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _dataset_for_horizon(
        self,
        *,
        symbol: str,
        interval: str,
        horizon_bars: int,
    ) -> tuple[pd.DataFrame, int]:
        original = int(
            self._forward_horizon_bars
        )
        self._forward_horizon_bars = int(
            horizon_bars
        )
        try:
            return self.build_dataset(
                symbol=symbol,
                interval=interval,
                include_target=True,
            )
        finally:
            self._forward_horizon_bars = (
                original
            )

    @staticmethod
    def _take_probability(
        model: Any,
        frame: pd.DataFrame,
    ) -> np.ndarray:
        probabilities = model.predict_proba(
            frame[META_FEATURE_COLUMNS]
        )
        classes = [
            int(value)
            for value in model.classes_
        ]
        if 1 not in classes:
            return np.zeros(
                len(frame),
                dtype=float,
            )
        return probabilities[
            :,
            classes.index(1),
        ]

    def _calibration_threshold(
        self,
        *,
        model: Any,
        calibration: pd.DataFrame,
    ) -> float:
        event_mask = (
            calibration["event_direction"]
            != 0
        )
        events = calibration.loc[
            event_mask
        ].copy()

        if (
            len(events) < 40
            or events["meta_target"].nunique() < 2
        ):
            return 1.0

        probabilities = self._take_probability(
            model,
            events,
        )
        best_threshold = 1.0
        best_score = float("-inf")
        event_indices = np.flatnonzero(
            event_mask.to_numpy()
        )

        for threshold in META_THRESHOLD_GRID:
            selected = (
                probabilities
                >= float(threshold)
            )
            positions = np.zeros(
                len(calibration),
                dtype=int,
            )
            positions[
                event_indices[selected]
            ] = (
                events.loc[
                    selected,
                    "event_direction",
                ]
                .to_numpy(dtype=int)
            )

            backtest = self.simulate(
                positions=positions,
                forward_returns=(
                    calibration[
                        "forward_return"
                    ]
                    .to_numpy(dtype=float)
                ),
            )

            if backtest.trade_count < 20:
                continue

            score = (
                backtest.net_return
                - 0.50
                * backtest.maximum_drawdown
                + 0.02
                * backtest.sharpe_like
            )

            if score > best_score:
                best_score = score
                best_threshold = float(
                    threshold
                )

        return best_threshold

    def evaluate_event_candidate(
        self,
        *,
        research: pd.DataFrame,
        family: str,
        model_name: str,
        model_config: dict[str, Any],
    ) -> dict[str, Any]:
        frame = apply_event_family(
            research,
            family=family,
            round_trip_cost_bps=(
                self._v41_round_trip_cost_bps
            ),
        )

        minimum_training_rows = max(
            500,
            int(self._minimum_regime_rows),
        )
        available_rows = len(frame)
        validation_rows = max(
            1,
            available_rows
            // (
                self._walk_forward_folds
                + 1
            ),
        )

        folds: list[dict[str, Any]] = []
        all_positions: list[np.ndarray] = []
        all_returns: list[np.ndarray] = []
        thresholds: list[float] = []
        all_meta_actual: list[np.ndarray] = []
        all_meta_predicted: list[np.ndarray] = []

        for fold_number in range(
            1,
            self._walk_forward_folds + 1,
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

            train = frame.iloc[
                :training_end
            ].copy()
            validation = frame.iloc[
                validation_start:
                validation_end
            ].copy()

            calibration_rows = max(
                100,
                int(
                    len(train)
                    * self._inner_calibration_fraction
                ),
            )
            if calibration_rows >= len(train):
                calibration_rows = max(
                    1,
                    len(train) // 5,
                )

            training = train.iloc[
                :-calibration_rows
            ].copy()
            calibration = train.iloc[
                -calibration_rows:
            ].copy()

            training_events = (
                training.loc[
                    training["event_direction"]
                    != 0
                ]
                .copy()
            )

            if (
                len(training_events) < 100
                or training_events[
                    "meta_target"
                ].nunique()
                < 2
            ):
                continue

            model = create_meta_model(
                model_config
            )
            model.fit(
                training_events[
                    META_FEATURE_COLUMNS
                ],
                training_events[
                    "meta_target"
                ],
            )

            threshold = (
                self._calibration_threshold(
                    model=model,
                    calibration=calibration,
                )
            )

            train_events = (
                train.loc[
                    train["event_direction"]
                    != 0
                ]
                .copy()
            )

            if (
                len(train_events) < 100
                or train_events[
                    "meta_target"
                ].nunique()
                < 2
            ):
                continue

            model = create_meta_model(
                model_config
            )
            model.fit(
                train_events[
                    META_FEATURE_COLUMNS
                ],
                train_events[
                    "meta_target"
                ],
            )

            event_mask = (
                validation["event_direction"]
                != 0
            )
            events = validation.loc[
                event_mask
            ].copy()
            positions = np.zeros(
                len(validation),
                dtype=int,
            )

            if (
                len(events) > 0
                and threshold < 1.0
            ):
                take_probability = (
                    self._take_probability(
                        model,
                        events,
                    )
                )
                selected = (
                    take_probability
                    >= threshold
                )
                event_indices = (
                    np.flatnonzero(
                        event_mask.to_numpy()
                    )
                )
                positions[
                    event_indices[selected]
                ] = (
                    events.loc[
                        selected,
                        "event_direction",
                    ]
                    .to_numpy(dtype=int)
                )

                all_meta_actual.append(
                    events[
                        "meta_target"
                    ].to_numpy(dtype=int)
                )
                all_meta_predicted.append(
                    selected.astype(int)
                )

            backtest = self.simulate(
                positions=positions,
                forward_returns=validation[
                    "forward_return"
                ].to_numpy(dtype=float),
            )

            folds.append(
                {
                    "fold": fold_number,
                    "threshold": float(
                        threshold
                    ),
                    "event_rows": int(
                        len(events)
                    ),
                    "net_return": float(
                        backtest.net_return
                    ),
                    "trade_count": int(
                        backtest.trade_count
                    ),
                    "maximum_drawdown": float(
                        backtest.maximum_drawdown
                    ),
                    "sharpe_like": float(
                        backtest.sharpe_like
                    ),
                }
            )
            all_positions.append(
                positions
            )
            all_returns.append(
                validation[
                    "forward_return"
                ].to_numpy(dtype=float)
            )
            thresholds.append(
                float(threshold)
            )

        if not folds:
            raise RuntimeError(
                "No valid V4.6 event folds."
            )

        positions = np.concatenate(
            all_positions
        )
        forward_returns = np.concatenate(
            all_returns
        )
        backtest = self.simulate(
            positions=positions,
            forward_returns=forward_returns,
        )

        if all_meta_actual:
            actual = np.concatenate(
                all_meta_actual
            )
            predicted = np.concatenate(
                all_meta_predicted
            )
            meta_balanced_accuracy = float(
                balanced_accuracy_score(
                    actual,
                    predicted,
                )
            )
            meta_f1 = float(
                f1_score(
                    actual,
                    predicted,
                    zero_division=0,
                )
            )
            meta_precision = float(
                precision_score(
                    actual,
                    predicted,
                    zero_division=0,
                )
            )
        else:
            meta_balanced_accuracy = 0.5
            meta_f1 = 0.0
            meta_precision = 0.0

        fold_returns = [
            float(item["net_return"])
            for item in folds
        ]
        finite_thresholds = [
            value
            for value in thresholds
            if value < 1.0
        ]
        selected_threshold = (
            float(
                np.median(
                    finite_thresholds
                )
            )
            if finite_thresholds
            else 1.0
        )

        return {
            "event_family": family,
            "model_name": model_name,
            "model_config": dict(
                model_config
            ),
            "selected_threshold": (
                selected_threshold
            ),
            "net_return": float(
                backtest.net_return
            ),
            "trade_count": int(
                backtest.trade_count
            ),
            "maximum_drawdown": float(
                backtest.maximum_drawdown
            ),
            "sharpe_like": float(
                backtest.sharpe_like
            ),
            "positive_fold_fraction": float(
                np.mean(
                    [
                        value > 0.0
                        for value in fold_returns
                    ]
                )
            ),
            "worst_fold_return": float(
                min(fold_returns)
            ),
            "meta_balanced_accuracy": (
                meta_balanced_accuracy
            ),
            "meta_f1": meta_f1,
            "meta_precision": (
                meta_precision
            ),
            "fold_returns": fold_returns,
            "folds": folds,
        }

    def run_event_discovery(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> dict[str, Any]:
        leaderboard: list[
            dict[str, Any]
        ] = []

        for horizon in HORIZONS:
            dataset, rows_loaded = (
                self._dataset_for_horizon(
                    symbol=symbol,
                    interval=interval,
                    horizon_bars=horizon,
                )
            )
            discovery, _, _ = (
                split_discovery_locked_final(
                    dataset
                )
            )

            for family in EVENT_FAMILIES:
                for (
                    model_name,
                    model_config,
                ) in MODEL_CONFIGS.items():
                    try:
                        result = (
                            self
                            .evaluate_event_candidate(
                                research=discovery,
                                family=family,
                                model_name=model_name,
                                model_config=(
                                    model_config
                                ),
                            )
                        )
                    except RuntimeError as exc:
                        result = {
                            "event_family": family,
                            "model_name": model_name,
                            "model_config": dict(
                                model_config
                            ),
                            "selected_threshold": 1.0,
                            "net_return": 0.0,
                            "trade_count": 0,
                            "maximum_drawdown": 0.0,
                            "sharpe_like": 0.0,
                            "positive_fold_fraction": 0.0,
                            "worst_fold_return": 0.0,
                            "meta_balanced_accuracy": 0.5,
                            "meta_f1": 0.0,
                            "meta_precision": 0.0,
                            "fold_returns": [],
                            "folds": [],
                            "error": str(exc),
                        }

                    result[
                        "horizon_bars"
                    ] = horizon
                    result[
                        "rows_loaded"
                    ] = int(rows_loaded)
                    leaderboard.append(
                        result
                    )

        leaderboard.sort(
            key=lambda item: (
                float(
                    item.get(
                        "positive_fold_fraction",
                        0.0,
                    )
                ),
                float(
                    item.get(
                        "net_return",
                        0.0,
                    )
                ),
                float(
                    item.get(
                        "meta_balanced_accuracy",
                        0.0,
                    )
                ),
            ),
            reverse=True,
        )

        payload = {
            "version": self.VERSION,
            "symbol": symbol.upper(),
            "interval": interval.lower(),
            "research_only": True,
            "locked_validation_opened": False,
            "final_test_opened": False,
            "governance_weakened": False,
            "trial_count": len(
                leaderboard
            ),
            "leaderboard": leaderboard,
        }

        write_json(
            self._v46_artifact_directory
            / "v46_event_discovery.json",
            payload,
        )
        return payload
