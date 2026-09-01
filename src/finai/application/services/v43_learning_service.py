from __future__ import annotations

import json
from dataclasses import asdict
from datetime import (
    UTC,
    datetime,
)
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone

from finai.application.services.v38_learning_service import (
    V38BacktestMetrics,
    V38FoldMetrics,
    V38LearningCycleResult,
    V38ModelEvaluation,
)
from finai.application.services.v421_learning_service import (
    V421LearningService,
)
from finai.domain.learning.v41_features import (
    V41_FEATURE_COLUMNS,
)
from finai.domain.learning.v43_research import (
    BUY,
    HOLD,
    SELL,
    classification_diagnostics,
    confidence_bucket_diagnostics,
    event_trade_metrics,
    multiclass_brier_score,
    probability_columns,
)


class V43LearningService(V421LearningService):
    """
    V4.3 confidence-calibrated,
    cost-aware abstention research.

    V4.3 preserves:

    - V4.2.1 non-overlapping fixed-horizon backtest
    - V4.2.1 one complete round-trip cost per trade
    - DST-aware New York session features
    - existing historical qualification gates
    - prospective shadow validation
    - paper-only champion governance

    V4.3 adds:

    - HOLD-aware directional decisions
    - >= 0.50 probability floor
    - expanded conservative threshold grid
    - positive calibration expectancy requirement
    - chronological calibration-slice stability
    - neighboring-threshold robustness
    - explicit no-trade fallback
    - out-of-fold confidence bucket diagnostics
    - per-class confusion diagnostics
    - multiclass Brier score
    """

    VERSION = "4.3"

    LEARNING_ARCHITECTURE = "confidence_calibrated_cost_aware_abstention_regime_ensemble"

    MINIMUM_SIGNAL_PROBABILITY = 0.50

    CALIBRATION_SLICE_COUNT = 3

    MINIMUM_POSITIVE_SLICE_FRACTION = 2.0 / 3.0

    MINIMUM_NEIGHBOR_POSITIVE_FRACTION = 0.50

    V43_THRESHOLD_GRID = (
        0.50,
        0.525,
        0.55,
        0.575,
        0.60,
        0.625,
        0.65,
        0.675,
        0.70,
        0.725,
        0.75,
        0.775,
        0.80,
    )

    def __init__(
        self,
        *,
        diagnostic_directory: str = ("artifacts/v43"),
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        self._v43_diagnostic_directory = Path(diagnostic_directory)

        self._v43_diagnostic_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._v43_model_diagnostics: dict[
            str,
            dict[str, Any],
        ] = {}

        self._v43_threshold_diagnostics: dict[
            str,
            Any,
        ] = {}

    @staticmethod
    def _write_json(
        *,
        path: Path,
        payload: Any,
    ) -> None:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            json.dumps(
                payload,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _load_json(
        path: Path,
    ) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))

        if not isinstance(
            payload,
            dict,
        ):
            raise RuntimeError(f"Expected JSON object: {path}")

        return payload

    @classmethod
    def positions_from_probabilities(
        cls,
        *,
        probabilities: np.ndarray,
        classes: np.ndarray,
        long_threshold: float,
        short_threshold: float,
    ) -> np.ndarray:
        """
        V4.3 changes one important V4.1 behavior.

        A directional class must now beat BOTH:

        - the opposite directional probability
        - the HOLD probability

        Therefore a model prediction such as:

            LONG  = 0.40
            HOLD  = 0.50
            SHORT = 0.10

        remains HOLD instead of opening LONG.
        """

        (
            short_probability,
            hold_probability,
            long_probability,
        ) = probability_columns(
            probabilities=probabilities,
            classes=classes,
        )

        effective_long_threshold = max(
            float(long_threshold),
            cls.MINIMUM_SIGNAL_PROBABILITY,
        )

        effective_short_threshold = max(
            float(short_threshold),
            cls.MINIMUM_SIGNAL_PROBABILITY,
        )

        positions = np.full(
            len(probabilities),
            HOLD,
            dtype=int,
        )

        long_mask = (
            (long_probability >= effective_long_threshold)
            & (long_probability > short_probability)
            & (long_probability > hold_probability)
        )

        short_mask = (
            (short_probability >= effective_short_threshold)
            & (short_probability > long_probability)
            & (short_probability > hold_probability)
        )

        positions[long_mask] = BUY

        positions[short_mask] = SELL

        return positions

    def _candidate_thresholds(
        self,
    ) -> tuple[
        float,
        ...,
    ]:
        inherited = list(self._long_probability_thresholds) + list(
            self._short_probability_thresholds
        )

        combined = list(self.V43_THRESHOLD_GRID) + [
            float(value) for value in inherited if (float(value) >= self.MINIMUM_SIGNAL_PROBABILITY)
        ]

        return tuple(sorted(set(combined)))

    def _calibration_slice_metrics(
        self,
        *,
        positions: np.ndarray,
        forward_returns: np.ndarray,
    ) -> list[dict[str, Any]]:
        positions = np.asarray(
            positions,
            dtype=int,
        )

        forward_returns = np.asarray(
            forward_returns,
            dtype=float,
        )

        slices = np.array_split(
            np.arange(len(positions)),
            self.CALIBRATION_SLICE_COUNT,
        )

        output: list[dict[str, Any]] = []

        for slice_number, indices in enumerate(
            slices,
            start=1,
        ):
            if len(indices) == 0:
                continue

            slice_positions = positions[indices]

            slice_returns = forward_returns[indices]

            backtest = self.simulate(
                positions=(slice_positions),
                forward_returns=(slice_returns),
            )

            output.append(
                {
                    "slice": slice_number,
                    "trade_count": (backtest.trade_count),
                    "net_return": (backtest.net_return),
                    "maximum_drawdown": (backtest.maximum_drawdown),
                    "sharpe_like": (backtest.sharpe_like),
                }
            )

        return output

    def _threshold_pair_metrics(
        self,
        *,
        probabilities: np.ndarray,
        classes: np.ndarray,
        forward_returns: np.ndarray,
        long_threshold: float,
        short_threshold: float,
    ) -> dict[str, Any]:
        positions = self.positions_from_probabilities(
            probabilities=probabilities,
            classes=classes,
            long_threshold=(long_threshold),
            short_threshold=(short_threshold),
        )

        backtest = self.simulate(
            positions=positions,
            forward_returns=(forward_returns),
        )

        trade_metrics = event_trade_metrics(
            positions=positions,
            forward_returns=(forward_returns),
            horizon=(self._forward_horizon_bars),
            round_trip_cost_bps=(self._v41_round_trip_cost_bps),
        )

        slice_metrics = self._calibration_slice_metrics(
            positions=positions,
            forward_returns=(forward_returns),
        )

        eligible_slices = [item for item in slice_metrics if (item["trade_count"] > 0)]

        if eligible_slices:
            positive_slice_fraction = float(
                np.mean([item["net_return"] > 0.0 for item in eligible_slices])
            )

            worst_slice_return = float(min(item["net_return"] for item in eligible_slices))
        else:
            positive_slice_fraction = 0.0
            worst_slice_return = 0.0

        return {
            "long_threshold": float(long_threshold),
            "short_threshold": float(short_threshold),
            "backtest": backtest,
            "trade_metrics": (trade_metrics),
            "slice_metrics": (slice_metrics),
            "positive_slice_fraction": (positive_slice_fraction),
            "worst_slice_return": (worst_slice_return),
        }

    @staticmethod
    def _neighbor_keys(
        *,
        long_index: int,
        short_index: int,
        threshold_count: int,
    ) -> list[tuple[int, int]]:
        neighbors: list[tuple[int, int]] = []

        for (
            long_delta,
            short_delta,
        ) in (
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
        ):
            candidate_long = long_index + long_delta

            candidate_short = short_index + short_delta

            if (
                candidate_long < 0
                or candidate_short < 0
                or candidate_long >= threshold_count
                or candidate_short >= threshold_count
            ):
                continue

            neighbors.append(
                (
                    candidate_long,
                    candidate_short,
                )
            )

        return neighbors

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
        probabilities = model.predict_proba(calibration[V41_FEATURE_COLUMNS])

        forward_returns = calibration["forward_return"].to_numpy(dtype=float)

        thresholds = self._candidate_thresholds()

        candidate_map: dict[
            tuple[int, int],
            dict[str, Any],
        ] = {}

        for (
            long_index,
            long_threshold,
        ) in enumerate(thresholds):
            for (
                short_index,
                short_threshold,
            ) in enumerate(thresholds):
                metrics = self._threshold_pair_metrics(
                    probabilities=(probabilities),
                    classes=(model.classes_),
                    forward_returns=(forward_returns),
                    long_threshold=(long_threshold),
                    short_threshold=(short_threshold),
                )

                candidate_map[
                    (
                        long_index,
                        short_index,
                    )
                ] = metrics

        eligible: list[dict[str, Any]] = []

        threshold_count = len(thresholds)

        for (
            key,
            metrics,
        ) in candidate_map.items():
            backtest = metrics["backtest"]

            trade_metrics = metrics["trade_metrics"]

            if backtest.trade_count < self._minimum_trades:
                continue

            # Cost-aware expectancy must be
            # positive before the configuration
            # can be considered executable.
            if trade_metrics["mean_net_bps"] <= 0.0:
                continue

            if backtest.net_return <= 0.0:
                continue

            if metrics["positive_slice_fraction"] < (self.MINIMUM_POSITIVE_SLICE_FRACTION):
                continue

            neighbor_keys = self._neighbor_keys(
                long_index=key[0],
                short_index=key[1],
                threshold_count=(threshold_count),
            )

            neighbor_results = [candidate_map[neighbor] for neighbor in neighbor_keys]

            eligible_neighbors = [
                item
                for item in neighbor_results
                if (item["backtest"].trade_count >= self._minimum_trades)
            ]

            if eligible_neighbors:
                neighbor_positive_fraction = float(
                    np.mean([item["backtest"].net_return >= 0.0 for item in eligible_neighbors])
                )
            else:
                neighbor_positive_fraction = 0.0

            if neighbor_positive_fraction < (self.MINIMUM_NEIGHBOR_POSITIVE_FRACTION):
                continue

            robust_score = (
                float(backtest.net_return)
                - (float(backtest.maximum_drawdown) * 0.50)
                + (float(backtest.sharpe_like) * 0.02)
                + (float(metrics["positive_slice_fraction"]) * 0.05)
                + (float(neighbor_positive_fraction) * 0.05)
                + (float(trade_metrics["mean_net_bps"]) / 10_000.0)
            )

            metrics["neighbor_positive_fraction"] = neighbor_positive_fraction

            metrics["robust_score"] = robust_score

            eligible.append(metrics)

        if not eligible:
            zero_positions = np.zeros(
                len(calibration),
                dtype=int,
            )

            no_trade_backtest = self.simulate(
                positions=(zero_positions),
                forward_returns=(forward_returns),
            )

            self._v43_threshold_diagnostics["latest"] = {
                "eligible_threshold_count": 0,
                "selected_long_threshold": 1.0,
                "selected_short_threshold": 1.0,
                "abstained": True,
                "reason": (
                    "No threshold pair satisfied "
                    "V4.3 positive-expectancy and "
                    "stability requirements."
                ),
            }

            return (
                1.0,
                1.0,
                no_trade_backtest,
            )

        winner = max(
            eligible,
            key=lambda item: item["robust_score"],
        )

        winner_backtest = winner["backtest"]

        self._v43_threshold_diagnostics["latest"] = {
            "eligible_threshold_count": (len(eligible)),
            "selected_long_threshold": (winner["long_threshold"]),
            "selected_short_threshold": (winner["short_threshold"]),
            "abstained": False,
            "positive_slice_fraction": (winner["positive_slice_fraction"]),
            "neighbor_positive_fraction": (winner["neighbor_positive_fraction"]),
            "mean_net_bps": (winner["trade_metrics"]["mean_net_bps"]),
            "median_net_bps": (winner["trade_metrics"]["median_net_bps"]),
            "robust_score": (winner["robust_score"]),
        }

        return (
            float(winner["long_threshold"]),
            float(winner["short_threshold"]),
            winner_backtest,
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

        available_rows = len(research)

        if available_rows <= minimum_training_rows:
            raise RuntimeError("Insufficient V4.3 research rows for walk-forward evaluation.")

        validation_rows = max(
            1,
            available_rows // (self._walk_forward_folds + 1),
        )

        folds: list[V38FoldMetrics] = []

        all_actual: list[np.ndarray] = []

        all_positions: list[np.ndarray] = []

        all_returns: list[np.ndarray] = []

        all_short_probability: list[np.ndarray] = []

        all_hold_probability: list[np.ndarray] = []

        all_long_probability: list[np.ndarray] = []

        long_thresholds: list[float] = []

        short_thresholds: list[float] = []

        fold_threshold_details: list[dict[str, Any]] = []

        for fold_number in range(
            1,
            self._walk_forward_folds + 1,
        ):
            validation_end = (
                available_rows - (self._walk_forward_folds - fold_number) * validation_rows
            )

            validation_start = validation_end - validation_rows

            training_end = validation_start - self._purge_rows

            if training_end <= minimum_training_rows:
                continue

            train = research.iloc[:training_end].copy()

            validation = research.iloc[validation_start:validation_end].copy()

            calibration_rows = max(
                100,
                int(len(train) * (self._inner_calibration_fraction)),
            )

            if calibration_rows >= len(train):
                calibration_rows = max(
                    1,
                    len(train) // 5,
                )

            training = train.iloc[:-calibration_rows]

            calibration = train.iloc[-calibration_rows:]

            model = clone(model_template)

            model.fit(
                training[V41_FEATURE_COLUMNS],
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

            threshold_detail = dict(
                self._v43_threshold_diagnostics.get(
                    "latest",
                    {},
                )
            )

            threshold_detail["fold"] = fold_number

            fold_threshold_details.append(threshold_detail)

            model.fit(
                train[V41_FEATURE_COLUMNS],
                train["target"],
            )

            probabilities = model.predict_proba(validation[V41_FEATURE_COLUMNS])

            (
                short_probability,
                hold_probability,
                long_probability,
            ) = probability_columns(
                probabilities=probabilities,
                classes=model.classes_,
            )

            positions = self.positions_from_probabilities(
                probabilities=(probabilities),
                classes=(model.classes_),
                long_threshold=(long_threshold),
                short_threshold=(short_threshold),
            )

            actual = validation["target"].to_numpy(dtype=int)

            (
                balanced_accuracy,
                macro_f1,
            ) = self._classification_metrics(
                actual=actual,
                predicted=positions,
            )

            forward_returns = validation["forward_return"].to_numpy(dtype=float)

            backtest = self.simulate(
                positions=positions,
                forward_returns=(forward_returns),
            )

            folds.append(
                V38FoldMetrics(
                    fold=fold_number,
                    long_threshold=(long_threshold),
                    short_threshold=(short_threshold),
                    balanced_accuracy=(balanced_accuracy),
                    macro_f1=(macro_f1),
                    net_return=(backtest.net_return),
                    trade_count=(backtest.trade_count),
                    turnover=(backtest.turnover),
                    maximum_drawdown=(backtest.maximum_drawdown),
                    sharpe_like=(backtest.sharpe_like),
                )
            )

            all_actual.append(actual)

            all_positions.append(positions)

            all_returns.append(forward_returns)

            all_short_probability.append(short_probability)

            all_hold_probability.append(hold_probability)

            all_long_probability.append(long_probability)

            long_thresholds.append(long_threshold)

            short_thresholds.append(short_threshold)

        if not folds:
            raise RuntimeError("V4.3 produced no valid walk-forward folds.")

        actual = np.concatenate(all_actual)

        positions = np.concatenate(all_positions)

        forward_returns = np.concatenate(all_returns)

        short_probability = np.concatenate(all_short_probability)

        hold_probability = np.concatenate(all_hold_probability)

        long_probability = np.concatenate(all_long_probability)

        (
            balanced_accuracy,
            macro_f1,
        ) = self._classification_metrics(
            actual=actual,
            predicted=positions,
        )

        backtest = self.simulate(
            positions=positions,
            forward_returns=(forward_returns),
        )

        positive_fold_fraction = float(np.mean([fold.net_return > 0.0 for fold in folds]))

        worst_fold_return = float(min(fold.net_return for fold in folds))

        composite = self._composite_score(
            balanced_accuracy=(balanced_accuracy),
            macro_f1=(macro_f1),
            net_return=(backtest.net_return),
            maximum_drawdown=(backtest.maximum_drawdown),
            positive_fold_fraction=(positive_fold_fraction),
        )

        confusion = classification_diagnostics(
            actual=actual,
            predicted=positions,
        )

        buckets = confidence_bucket_diagnostics(
            short_probability=(short_probability),
            hold_probability=(hold_probability),
            long_probability=(long_probability),
            forward_returns=(forward_returns),
            horizon=(self._forward_horizon_bars),
            round_trip_cost_bps=(self._v41_round_trip_cost_bps),
        )

        brier = multiclass_brier_score(
            actual=actual,
            short_probability=(short_probability),
            hold_probability=(hold_probability),
            long_probability=(long_probability),
        )

        self._v43_model_diagnostics[model_name] = {
            "model_name": (model_name),
            "walk_forward": {
                "balanced_accuracy": (balanced_accuracy),
                "macro_f1": (macro_f1),
                "net_return": (backtest.net_return),
                "trade_count": (backtest.trade_count),
                "maximum_drawdown": (backtest.maximum_drawdown),
                "positive_fold_fraction": (positive_fold_fraction),
                "worst_fold_return": (worst_fold_return),
            },
            "probability_quality": {
                "multiclass_brier_score": (brier),
            },
            "classification": (confusion),
            "confidence_buckets": (buckets),
            "threshold_selection": (fold_threshold_details),
        }

        return V38ModelEvaluation(
            model_name=model_name,
            long_threshold=float(np.median(long_thresholds)),
            short_threshold=float(np.median(short_thresholds)),
            balanced_accuracy=(balanced_accuracy),
            macro_f1=(macro_f1),
            net_return=(backtest.net_return),
            trade_count=(backtest.trade_count),
            turnover=(backtest.turnover),
            maximum_drawdown=(backtest.maximum_drawdown),
            sharpe_like=(backtest.sharpe_like),
            positive_fold_fraction=(positive_fold_fraction),
            worst_fold_return=(worst_fold_return),
            composite_score=(composite),
            folds=folds,
        )

    def _holdout_diagnostics(
        self,
        *,
        model: Any,
        holdout: pd.DataFrame,
        long_threshold: float,
        short_threshold: float,
    ) -> dict[str, Any]:
        probabilities = model.predict_proba(holdout[V41_FEATURE_COLUMNS])

        (
            short_probability,
            hold_probability,
            long_probability,
        ) = probability_columns(
            probabilities=probabilities,
            classes=model.classes_,
        )

        positions = self.positions_from_probabilities(
            probabilities=probabilities,
            classes=model.classes_,
            long_threshold=(long_threshold),
            short_threshold=(short_threshold),
        )

        actual = holdout["target"].to_numpy(dtype=int)

        forward_returns = holdout["forward_return"].to_numpy(dtype=float)

        return {
            "classification": (
                classification_diagnostics(
                    actual=actual,
                    predicted=positions,
                )
            ),
            "probability_quality": {
                "multiclass_brier_score": (
                    multiclass_brier_score(
                        actual=actual,
                        short_probability=(short_probability),
                        hold_probability=(hold_probability),
                        long_probability=(long_probability),
                    )
                )
            },
            "confidence_buckets": (
                confidence_bucket_diagnostics(
                    short_probability=(short_probability),
                    hold_probability=(hold_probability),
                    long_probability=(long_probability),
                    forward_returns=(forward_returns),
                    horizon=(self._forward_horizon_bars),
                    round_trip_cost_bps=(self._v41_round_trip_cost_bps),
                )
            ),
        }

    def run_learning_cycle(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> V38LearningCycleResult:
        result = super().run_learning_cycle(
            symbol=symbol,
            interval=interval,
        )

        candidate_path = Path(result.candidate_path)

        candidate_metadata_path = Path(result.candidate_metadata_path)

        candidate_metadata = self._load_json(candidate_metadata_path)

        normalized_symbol = symbol.strip().upper()

        normalized_interval = interval.strip().lower()

        (
            dataset,
            _,
        ) = self.build_dataset(
            symbol=normalized_symbol,
            interval=normalized_interval,
            include_target=True,
        )

        holdout_rows = max(
            1,
            int(len(dataset) * self._holdout_fraction),
        )

        research_end = len(dataset) - holdout_rows - self._purge_rows

        research = dataset.iloc[:research_end].copy()

        holdout = dataset.iloc[-holdout_rows:].copy()

        winner_name = result.winning_model

        model_templates = self.create_model_templates()

        winning_model = clone(model_templates[winner_name])

        winning_model.fit(
            research[V41_FEATURE_COLUMNS],
            research["target"],
        )

        holdout_diagnostics = self._holdout_diagnostics(
            model=winning_model,
            holdout=holdout,
            long_threshold=(result.selected_long_threshold),
            short_threshold=(result.selected_short_threshold),
        )

        completed_at = datetime.now(UTC)

        timestamp = completed_at.strftime("%Y%m%dT%H%M%SZ")

        diagnostics_payload = {
            "version": self.VERSION,
            "learning_architecture": (self.LEARNING_ARCHITECTURE),
            "symbol": (normalized_symbol),
            "interval": (normalized_interval),
            "candidate_path": str(candidate_path),
            "winning_model": (winner_name),
            "research_only_model_diagnostics": (self._v43_model_diagnostics),
            "holdout_reporting_only": (holdout_diagnostics),
            "threshold_policy": {
                "minimum_signal_probability": (self.MINIMUM_SIGNAL_PROBABILITY),
                "threshold_grid": list(self._candidate_thresholds()),
                "hold_probability_must_be_beaten": True,
                "minimum_positive_slice_fraction": (self.MINIMUM_POSITIVE_SLICE_FRACTION),
                "minimum_neighbor_positive_fraction": (self.MINIMUM_NEIGHBOR_POSITIVE_FRACTION),
                "positive_net_expectancy_required": True,
                "positive_calibration_return_required": True,
                "no_trade_fallback_enabled": True,
            },
            "holdout_usage": (
                "REPORTING ONLY. Holdout results are not used for threshold selection."
            ),
            "created_at": (completed_at.isoformat()),
        }

        diagnostics_path = self._v43_diagnostic_directory / (f"diagnostics_{timestamp}.json")

        latest_diagnostics_path = self._v43_diagnostic_directory / "latest_diagnostics.json"

        self._write_json(
            path=diagnostics_path,
            payload=diagnostics_payload,
        )

        self._write_json(
            path=(latest_diagnostics_path),
            payload=(diagnostics_payload),
        )

        candidate_metadata["version"] = self.VERSION

        candidate_metadata["learning_architecture"] = self.LEARNING_ARCHITECTURE

        candidate_metadata["v43_diagnostics_path"] = str(diagnostics_path)

        candidate_metadata["v43_threshold_policy"] = diagnostics_payload["threshold_policy"]

        candidate_metadata["holdout_usage"] = diagnostics_payload["holdout_usage"]

        self._write_json(
            path=(candidate_metadata_path),
            payload=(candidate_metadata),
        )

        latest_path = self._artifact_directory / "latest_learning_cycle.json"

        if latest_path.exists():
            latest_payload = self._load_json(latest_path)

            latest_payload["version"] = self.VERSION

            latest_payload["learning_architecture"] = self.LEARNING_ARCHITECTURE

            latest_payload["v43_diagnostics_path"] = str(diagnostics_path)

            latest_payload["v43_threshold_policy"] = diagnostics_payload["threshold_policy"]

            latest_payload["holdout_usage"] = diagnostics_payload["holdout_usage"]

            self._write_json(
                path=latest_path,
                payload=(latest_payload),
            )

        return result
