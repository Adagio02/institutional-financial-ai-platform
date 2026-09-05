from __future__ import annotations

from typing import Any

import numpy as np

from finai.application.services.v431_learning_service import (
    V431LearningService,
)


class V432LearningService(V431LearningService):
    """
    V4.3.2 sample-aware directional calibration.

    This release separates small calibration-window evidence from the
    larger global promotion trade-count requirement. Global historical,
    holdout, shadow, and champion gates remain inherited and unchanged.
    """

    VERSION = "4.3.2"
    LEARNING_ARCHITECTURE = (
        "sample_aware_directional_calibration_"
        "confidence_abstention_regime_ensemble"
    )

    DIRECTIONAL_CALIBRATION_MINIMUM_TRADES = 20
    NEIGHBOR_MINIMUM_TRADES = 10

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
            item
            for item in neighbors
            if (
                item["backtest"].trade_count
                >= self.NEIGHBOR_MINIMUM_TRADES
            )
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

            if (
                backtest.trade_count
                < self.DIRECTIONAL_CALIBRATION_MINIMUM_TRADES
            ):
                failure_reasons.append(
                    "directional_calibration_minimum_trade_count"
                )

            if trade_metrics["mean_net_bps"] <= 0.0:
                failure_reasons.append(
                    "non_positive_mean_net_bps"
                )

            if backtest.net_return <= 0.0:
                failure_reasons.append(
                    "non_positive_net_return"
                )

            if (
                item["positive_slice_fraction"]
                < self.MINIMUM_POSITIVE_SLICE_FRACTION
            ):
                failure_reasons.append(
                    "positive_slice_fraction"
                )

            if (
                neighbor_fraction
                < self.MINIMUM_NEIGHBOR_POSITIVE_FRACTION
            ):
                failure_reasons.append(
                    "neighbor_positive_fraction"
                )

            diagnostic = {
                "threshold": float(item["threshold"]),
                "trade_count": int(backtest.trade_count),
                "net_return": float(backtest.net_return),
                "maximum_drawdown": float(
                    backtest.maximum_drawdown
                ),
                "sharpe_like": float(backtest.sharpe_like),
                "mean_net_bps": float(
                    trade_metrics["mean_net_bps"]
                ),
                "median_net_bps": float(
                    trade_metrics["median_net_bps"]
                ),
                "positive_slice_fraction": float(
                    item["positive_slice_fraction"]
                ),
                "worst_slice_return": float(
                    item["worst_slice_return"]
                ),
                "neighbor_positive_fraction": float(
                    neighbor_fraction
                ),
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
            candidate["neighbor_positive_fraction"] = (
                neighbor_fraction
            )
            candidate["robust_score"] = robust_score
            eligible.append(candidate)

        failure_counts = self._failure_counts(
            threshold_diagnostics
        )

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
                    "V4.3.2 sample-aware expectancy and stability "
                    "requirements."
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
                "threshold_diagnostics": (
                    threshold_diagnostics
                ),
                "calibration_minimum_trades": (
                    self.DIRECTIONAL_CALIBRATION_MINIMUM_TRADES
                ),
                "neighbor_minimum_trades": (
                    self.NEIGHBOR_MINIMUM_TRADES
                ),
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
            "reason": (
                "Direction satisfied V4.3.2 sample-aware "
                "expectancy and stability gates."
            ),
            "mean_net_bps": float(
                winner["trade_metrics"]["mean_net_bps"]
            ),
            "median_net_bps": float(
                winner["trade_metrics"]["median_net_bps"]
            ),
            "trade_count": int(
                winner["backtest"].trade_count
            ),
            "positive_slice_fraction": float(
                winner["positive_slice_fraction"]
            ),
            "neighbor_positive_fraction": float(
                winner["neighbor_positive_fraction"]
            ),
            "robust_score": float(
                winner["robust_score"]
            ),
            "failure_counts": failure_counts,
            "best_expectancy_candidate": best_expectancy,
            "best_return_candidate": best_return,
            "best_stability_candidate": best_stability,
            "threshold_diagnostics": threshold_diagnostics,
            "calibration_minimum_trades": (
                self.DIRECTIONAL_CALIBRATION_MINIMUM_TRADES
            ),
            "neighbor_minimum_trades": (
                self.NEIGHBOR_MINIMUM_TRADES
            ),
        }
