from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import (
    balanced_accuracy_score,
    f1_score,
)

from finai.application.services.v447_learning_service import (
    V447LearningService,
)
from finai.domain.learning.v44_research import (
    split_discovery_locked_final,
    write_json,
)
from finai.domain.learning.v45_features import (
    V45_FEATURE_COLUMNS,
    apply_v45_features,
)
from finai.domain.learning.v45_research import (
    DIRECTIONS,
    THRESHOLD_GRID,
    directional_positions,
)


class V45LearningService(V447LearningService):
    """
    V4.5 signal-engineering research.

    This release is discovery-only. It does not open V4.4 locked or final
    partitions and cannot promote a champion.
    """

    VERSION = "4.5"
    LEARNING_ARCHITECTURE = (
        "causal_signal_engineering_"
        "discovery_only"
    )

    def __init__(
        self,
        *,
        v45_artifact_directory: str = "artifacts/v45",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._v45_artifact_directory = Path(
            v45_artifact_directory
        )
        self._v45_artifact_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    @property
    def feature_columns(
        self,
    ) -> list[str]:
        return list(V45_FEATURE_COLUMNS)

    def build_dataset(
        self,
        *,
        symbol: str,
        interval: str,
        include_target: bool,
    ) -> tuple[pd.DataFrame, int]:
        dataset, rows_loaded = (
            super().build_dataset(
                symbol=symbol,
                interval=interval,
                include_target=include_target,
            )
        )
        return (
            apply_v45_features(dataset),
            rows_loaded,
        )

    def _threshold_on_calibration(
        self,
        *,
        model: Any,
        calibration: pd.DataFrame,
        feature_columns: list[str],
        direction: str,
    ) -> float:
        probabilities = model.predict_proba(
            calibration[feature_columns]
        )

        best_threshold = 1.0
        best_score = float("-inf")

        for threshold in THRESHOLD_GRID:
            positions = directional_positions(
                probabilities=probabilities,
                classes=model.classes_,
                threshold=threshold,
                direction=direction,
            )
            backtest = self.simulate(
                positions=positions,
                forward_returns=calibration[
                    "forward_return"
                ].to_numpy(dtype=float),
            )

            # Calibration minimum is deliberately smaller than the
            # promotion minimum. Promotion gates remain unchanged.
            if backtest.trade_count < 20:
                continue

            score = (
                backtest.net_return
                - 0.50 * backtest.maximum_drawdown
                + 0.02 * backtest.sharpe_like
            )
            if score > best_score:
                best_score = score
                best_threshold = float(threshold)

        return best_threshold

    def evaluate_feature_set(
        self,
        *,
        model_name: str,
        model_template: Any,
        research: pd.DataFrame,
        feature_columns: list[str],
        direction: str,
    ) -> dict[str, Any]:
        minimum_training_rows = max(
            500,
            int(self._minimum_regime_rows),
        )
        available_rows = len(research)
        if available_rows <= minimum_training_rows:
            raise RuntimeError(
                "Insufficient V4.5 research rows."
            )

        validation_rows = max(
            1,
            available_rows
            // (self._walk_forward_folds + 1),
        )

        folds: list[dict[str, Any]] = []
        all_actual: list[np.ndarray] = []
        all_positions: list[np.ndarray] = []
        all_returns: list[np.ndarray] = []

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
            if training_end <= minimum_training_rows:
                continue

            train = research.iloc[
                :training_end
            ].copy()
            validation = research.iloc[
                validation_start:validation_end
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

            model = clone(model_template)
            model.fit(
                training[feature_columns],
                training["target"],
            )

            threshold = (
                self._threshold_on_calibration(
                    model=model,
                    calibration=calibration,
                    feature_columns=feature_columns,
                    direction=direction,
                )
            )

            model.fit(
                train[feature_columns],
                train["target"],
            )
            probabilities = model.predict_proba(
                validation[feature_columns]
            )
            positions = directional_positions(
                probabilities=probabilities,
                classes=model.classes_,
                threshold=threshold,
                direction=direction,
            )

            actual = validation[
                "target"
            ].to_numpy(dtype=int)
            forward_returns = validation[
                "forward_return"
            ].to_numpy(dtype=float)

            balanced_accuracy = float(
                balanced_accuracy_score(
                    actual,
                    positions,
                )
            )
            macro_f1 = float(
                f1_score(
                    actual,
                    positions,
                    average="macro",
                    zero_division=0,
                )
            )
            backtest = self.simulate(
                positions=positions,
                forward_returns=forward_returns,
            )

            folds.append(
                {
                    "fold": fold_number,
                    "threshold": threshold,
                    "balanced_accuracy": (
                        balanced_accuracy
                    ),
                    "macro_f1": macro_f1,
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
            all_actual.append(actual)
            all_positions.append(positions)
            all_returns.append(forward_returns)

        if not folds:
            raise RuntimeError(
                "V4.5 produced no valid folds."
            )

        actual = np.concatenate(all_actual)
        positions = np.concatenate(all_positions)
        forward_returns = np.concatenate(
            all_returns
        )

        backtest = self.simulate(
            positions=positions,
            forward_returns=forward_returns,
        )

        return {
            "model_name": model_name,
            "direction": direction,
            "feature_count": len(
                feature_columns
            ),
            "balanced_accuracy": float(
                balanced_accuracy_score(
                    actual,
                    positions,
                )
            ),
            "macro_f1": float(
                f1_score(
                    actual,
                    positions,
                    average="macro",
                    zero_division=0,
                )
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
                        fold["net_return"] > 0.0
                        for fold in folds
                    ]
                )
            ),
            "worst_fold_return": float(
                min(
                    fold["net_return"]
                    for fold in folds
                )
            ),
            "fold_returns": [
                float(fold["net_return"])
                for fold in folds
            ],
            "folds": folds,
        }

    def run_signal_engineering(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> dict[str, Any]:
        dataset, rows_loaded = self.build_dataset(
            symbol=symbol,
            interval=interval,
            include_target=True,
        )
        discovery, _, _ = (
            split_discovery_locked_final(
                dataset
            )
        )

        model_templates = (
            self.create_model_templates()
        )
        leaderboard: list[
            dict[str, Any]
        ] = []

        # V4.5 establishes the full engineered baseline.
        # Directional specialization is expanded in V4.5.2.
        for model_name, template in (
            model_templates.items()
        ):
            for direction in DIRECTIONS:
                result = self.evaluate_feature_set(
                    model_name=model_name,
                    model_template=template,
                    research=discovery,
                    feature_columns=(
                        self.feature_columns
                    ),
                    direction=direction,
                )
                result["variant"] = (
                    "all_engineered"
                )
                leaderboard.append(result)

        leaderboard.sort(
            key=lambda item: (
                item[
                    "positive_fold_fraction"
                ],
                item["net_return"],
                -item[
                    "maximum_drawdown"
                ],
            ),
            reverse=True,
        )

        payload = {
            "version": self.VERSION,
            "symbol": symbol.upper(),
            "interval": interval.lower(),
            "rows_loaded": int(rows_loaded),
            "dataset_rows": int(
                len(dataset)
            ),
            "discovery_rows": int(
                len(discovery)
            ),
            "research_only": True,
            "locked_validation_opened": False,
            "final_test_opened": False,
            "governance_weakened": False,
            "feature_columns": (
                self.feature_columns
            ),
            "leaderboard": leaderboard,
        }

        write_json(
            self._v45_artifact_directory
            / "v45_signal_engineering.json",
            payload,
        )
        return payload
