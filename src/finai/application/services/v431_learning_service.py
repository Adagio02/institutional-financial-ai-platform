from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from finai.application.services.v38_learning_service import V38BacktestMetrics
from finai.application.services.v43_learning_service import V43LearningService
from finai.domain.learning.v41_features import V41_FEATURE_COLUMNS
from finai.domain.learning.v43_research import (
    BUY,
    HOLD,
    SELL,
    event_trade_metrics,
    probability_columns,
)


class V431LearningService(V43LearningService):
    """
    V4.3.1 directional asymmetric governance.

    LONG and SHORT are calibrated independently. Either direction may
    be disabled without forcing the other direction to fail.

    Every rejected threshold is retained in diagnostics. Historical,
    shadow, champion, and paper-only governance remain inherited.
    """

    VERSION = "4.3.1"
    LEARNING_ARCHITECTURE = (
        "directionally_asymmetric_confidence_calibrated_cost_aware_abstention_regime_ensemble"
    )
    DIRECTION_DISABLED_THRESHOLD = 1.0

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._v431_directional_diagnostics: dict[str, Any] = {}

    def _direction_positions(
        self,
        *,
        probabilities: np.ndarray,
        classes: np.ndarray,
        direction: str,
        threshold: float,
    ) -> np.ndarray:
        short_probability, hold_probability, long_probability = probability_columns(
            probabilities=probabilities,
            classes=classes,
        )

        positions = np.full(len(probabilities), HOLD, dtype=int)
        effective_threshold = max(
            float(threshold),
            self.MINIMUM_SIGNAL_PROBABILITY,
        )

        if direction == "long":
            mask = (
                (long_probability >= effective_threshold)
                & (long_probability > short_probability)
                & (long_probability > hold_probability)
            )
            positions[mask] = BUY
            return positions

        if direction == "short":
            mask = (
                (short_probability >= effective_threshold)
                & (short_probability > long_probability)
                & (short_probability > hold_probability)
            )
            positions[mask] = SELL
            return positions

        raise ValueError("direction must be 'long' or 'short'.")

    def _direction_slice_metrics(
        self,
        *,
        positions: np.ndarray,
        forward_returns: np.ndarray,
    ) -> list[dict[str, Any]]:
        positions = np.asarray(positions, dtype=int)
        forward_returns = np.asarray(forward_returns, dtype=float)

        slices = np.array_split(
            np.arange(len(positions)),
            self.CALIBRATION_SLICE_COUNT,
        )

        output: list[dict[str, Any]] = []

        for slice_number, indices in enumerate(slices, start=1):
            if len(indices) == 0:
                continue

            backtest = self.simulate(
                positions=positions[indices],
                forward_returns=forward_returns[indices],
            )

            output.append(
                {
                    "slice": slice_number,
                    "trade_count": int(backtest.trade_count),
                    "net_return": float(backtest.net_return),
                    "maximum_drawdown": float(backtest.maximum_drawdown),
                    "sharpe_like": float(backtest.sharpe_like),
                }
            )

        return output

    def _direction_threshold_metrics(
        self,
        *,
        probabilities: np.ndarray,
        classes: np.ndarray,
        forward_returns: np.ndarray,
        direction: str,
        threshold: float,
    ) -> dict[str, Any]:
        positions = self._direction_positions(
            probabilities=probabilities,
            classes=classes,
            direction=direction,
            threshold=threshold,
        )

        backtest = self.simulate(
            positions=positions,
            forward_returns=forward_returns,
        )

        trade_metrics = event_trade_metrics(
            positions=positions,
            forward_returns=forward_returns,
            horizon=self._forward_horizon_bars,
            round_trip_cost_bps=self._v41_round_trip_cost_bps,
        )

        slice_metrics = self._direction_slice_metrics(
            positions=positions,
            forward_returns=forward_returns,
        )

        active_slices = [item for item in slice_metrics if item["trade_count"] > 0]

        if active_slices:
            positive_slice_fraction = float(
                np.mean([item["net_return"] > 0.0 for item in active_slices])
            )
            worst_slice_return = float(min(item["net_return"] for item in active_slices))
        else:
            positive_slice_fraction = 0.0
            worst_slice_return = 0.0

        return {
            "direction": direction,
            "threshold": float(threshold),
            "positions": positions,
            "backtest": backtest,
            "trade_metrics": trade_metrics,
            "slice_metrics": slice_metrics,
            "positive_slice_fraction": positive_slice_fraction,
            "worst_slice_return": worst_slice_return,
        }

    def _direction_neighbor_fraction(
        self,
        *,
        candidate_index: int,
        metrics: list[dict[str, Any]],
    ) -> float:
        neighbors: list[dict[str, Any]] = []

        if candidate_index > 0:
            neighbors.append(metrics[candidate_index - 1])

        if candidate_index < len(metrics) - 1:
            neighbors.append(metrics[candidate_index + 1])

        eligible_neighbors = [
            item for item in neighbors if item["backtest"].trade_count >= self._minimum_trades
        ]

        if not eligible_neighbors:
            return 0.0

        return float(
            np.mean(
                [
                    (
                        item["backtest"].net_return > 0.0
                        and item["trade_metrics"]["mean_net_bps"] > 0.0
                    )
                    for item in eligible_neighbors
                ]
            )
        )

    @staticmethod
    def _failure_counts(
        threshold_diagnostics: list[dict[str, Any]],
    ) -> dict[str, int]:
        counts: dict[str, int] = {}

        for diagnostic in threshold_diagnostics:
            for reason in diagnostic["failure_reasons"]:
                counts[reason] = counts.get(reason, 0) + 1

        return counts

    def _optimize_direction(
        self,
        *,
        probabilities: np.ndarray,
        classes: np.ndarray,
        forward_returns: np.ndarray,
        direction: str,
    ) -> dict[str, Any]:
        thresholds = self._candidate_thresholds()

        raw_metrics = [
            self._direction_threshold_metrics(
                probabilities=probabilities,
                classes=classes,
                forward_returns=forward_returns,
                direction=direction,
                threshold=threshold,
            )
            for threshold in thresholds
        ]

        eligible: list[dict[str, Any]] = []
        threshold_diagnostics: list[dict[str, Any]] = []

        for index, item in enumerate(raw_metrics):
            backtest = item["backtest"]
            trade_metrics = item["trade_metrics"]
            neighbor_fraction = self._direction_neighbor_fraction(
                candidate_index=index,
                metrics=raw_metrics,
            )

            failure_reasons: list[str] = []

            if backtest.trade_count < self._minimum_trades:
                failure_reasons.append("minimum_trade_count")
            if trade_metrics["mean_net_bps"] <= 0.0:
                failure_reasons.append("non_positive_mean_net_bps")
            if backtest.net_return <= 0.0:
                failure_reasons.append("non_positive_net_return")
            if item["positive_slice_fraction"] < self.MINIMUM_POSITIVE_SLICE_FRACTION:
                failure_reasons.append("positive_slice_fraction")
            if neighbor_fraction < self.MINIMUM_NEIGHBOR_POSITIVE_FRACTION:
                failure_reasons.append("neighbor_positive_fraction")

            diagnostic = {
                "threshold": float(item["threshold"]),
                "trade_count": int(backtest.trade_count),
                "net_return": float(backtest.net_return),
                "maximum_drawdown": float(backtest.maximum_drawdown),
                "sharpe_like": float(backtest.sharpe_like),
                "mean_net_bps": float(trade_metrics["mean_net_bps"]),
                "median_net_bps": float(trade_metrics["median_net_bps"]),
                "positive_slice_fraction": float(item["positive_slice_fraction"]),
                "worst_slice_return": float(item["worst_slice_return"]),
                "neighbor_positive_fraction": float(neighbor_fraction),
                "eligible": not failure_reasons,
                "failure_reasons": failure_reasons,
            }

            threshold_diagnostics.append(diagnostic)

            if failure_reasons:
                continue

            robust_score = (
                float(backtest.net_return)
                - float(backtest.maximum_drawdown) * 0.50
                + float(backtest.sharpe_like) * 0.02
                + float(item["positive_slice_fraction"]) * 0.05
                + float(neighbor_fraction) * 0.05
                + float(trade_metrics["mean_net_bps"]) / 10_000.0
            )

            candidate = dict(item)
            candidate["neighbor_positive_fraction"] = neighbor_fraction
            candidate["robust_score"] = robust_score
            eligible.append(candidate)

        failure_counts = self._failure_counts(threshold_diagnostics)

        best_expectancy = None
        best_return = None
        best_stability = None

        if threshold_diagnostics:
            best_expectancy = max(
                threshold_diagnostics,
                key=lambda item: item["mean_net_bps"],
            )
            best_return = max(
                threshold_diagnostics,
                key=lambda item: item["net_return"],
            )
            best_stability = max(
                threshold_diagnostics,
                key=lambda item: (
                    item["positive_slice_fraction"],
                    item["neighbor_positive_fraction"],
                    item["mean_net_bps"],
                ),
            )

        if not eligible:
            return {
                "direction": direction,
                "enabled": False,
                "threshold": self.DIRECTION_DISABLED_THRESHOLD,
                "eligible_threshold_count": 0,
                "reason": (
                    f"No {direction.upper()} threshold satisfied "
                    "positive expectancy and stability requirements."
                ),
                "mean_net_bps": 0.0,
                "median_net_bps": 0.0,
                "trade_count": 0,
                "positive_slice_fraction": 0.0,
                "neighbor_positive_fraction": 0.0,
                "robust_score": None,
                "failure_counts": failure_counts,
                "best_expectancy_candidate": best_expectancy,
                "best_return_candidate": best_return,
                "best_stability_candidate": best_stability,
                "threshold_diagnostics": threshold_diagnostics,
            }

        winner = max(
            eligible,
            key=lambda item: item["robust_score"],
        )

        return {
            "direction": direction,
            "enabled": True,
            "threshold": float(winner["threshold"]),
            "eligible_threshold_count": len(eligible),
            "reason": ("Direction satisfied V4.3.1 expectancy and stability gates."),
            "mean_net_bps": float(winner["trade_metrics"]["mean_net_bps"]),
            "median_net_bps": float(winner["trade_metrics"]["median_net_bps"]),
            "trade_count": int(winner["backtest"].trade_count),
            "positive_slice_fraction": float(winner["positive_slice_fraction"]),
            "neighbor_positive_fraction": float(winner["neighbor_positive_fraction"]),
            "robust_score": float(winner["robust_score"]),
            "failure_counts": failure_counts,
            "best_expectancy_candidate": best_expectancy,
            "best_return_candidate": best_return,
            "best_stability_candidate": best_stability,
            "threshold_diagnostics": threshold_diagnostics,
        }

    def _optimize_thresholds(
        self,
        *,
        model: Any,
        calibration: pd.DataFrame,
    ) -> tuple[float, float, V38BacktestMetrics]:
        probabilities = model.predict_proba(calibration[V41_FEATURE_COLUMNS])
        forward_returns = calibration["forward_return"].to_numpy(dtype=float)

        long_result = self._optimize_direction(
            probabilities=probabilities,
            classes=model.classes_,
            forward_returns=forward_returns,
            direction="long",
        )
        short_result = self._optimize_direction(
            probabilities=probabilities,
            classes=model.classes_,
            forward_returns=forward_returns,
            direction="short",
        )

        long_threshold = float(long_result["threshold"])
        short_threshold = float(short_result["threshold"])

        combined_positions = self.positions_from_probabilities(
            probabilities=probabilities,
            classes=model.classes_,
            long_threshold=long_threshold,
            short_threshold=short_threshold,
        )

        combined_backtest = self.simulate(
            positions=combined_positions,
            forward_returns=forward_returns,
        )

        executable = bool(long_result["enabled"] or short_result["enabled"])

        latest = {
            "executable": executable,
            "long_enabled": bool(long_result["enabled"]),
            "short_enabled": bool(short_result["enabled"]),
            "selected_long_threshold": long_threshold,
            "selected_short_threshold": short_threshold,
            "long": long_result,
            "short": short_result,
            "combined": {
                "trade_count": int(combined_backtest.trade_count),
                "net_return": float(combined_backtest.net_return),
                "maximum_drawdown": float(combined_backtest.maximum_drawdown),
                "sharpe_like": float(combined_backtest.sharpe_like),
            },
        }

        self._v43_threshold_diagnostics["latest"] = latest
        self._v431_directional_diagnostics["latest"] = latest

        return (
            long_threshold,
            short_threshold,
            combined_backtest,
        )
