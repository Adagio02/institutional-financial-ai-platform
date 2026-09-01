from __future__ import annotations

from typing import Any

import numpy as np

from finai.application.services.v434_learning_service import (
    V434LearningService,
)


class V435LearningService(V434LearningService):
    """
    V4.3.5 uncertainty-aware directional expectancy.

    A direction must pass all inherited V4.3.4 gates and then show a
    non-negative bootstrap lower confidence bound for net expectancy.
    This prevents a tiny number of unusually profitable events from
    being treated as robust evidence.
    """

    VERSION = "4.3.5"
    LEARNING_ARCHITECTURE = (
        "bootstrap_uncertainty_probability_margin_regime_"
        "aware_sample_aware_directional_abstention_ensemble"
    )

    BOOTSTRAP_REPETITIONS = 1000
    BOOTSTRAP_CONFIDENCE_LEVEL = 0.90
    BOOTSTRAP_RANDOM_SEED = 4315

    @classmethod
    def bootstrap_mean_lower_bound(
        cls,
        values: np.ndarray,
    ) -> float:
        values = np.asarray(values, dtype=float)
        values = values[np.isfinite(values)]

        if len(values) == 0:
            return float("-inf")

        if len(values) == 1:
            return float(values[0])

        rng = np.random.default_rng(
            cls.BOOTSTRAP_RANDOM_SEED
        )

        sample_indices = rng.integers(
            0,
            len(values),
            size=(
                cls.BOOTSTRAP_REPETITIONS,
                len(values),
            ),
        )

        sample_means = np.mean(
            values[sample_indices],
            axis=1,
        )

        alpha = (
            1.0 - cls.BOOTSTRAP_CONFIDENCE_LEVEL
        )

        return float(
            np.quantile(
                sample_means,
                alpha,
            )
        )

    def _net_event_returns(
        self,
        *,
        positions: np.ndarray,
        forward_returns: np.ndarray,
    ) -> np.ndarray:
        positions = np.asarray(
            positions,
            dtype=int,
        )
        forward_returns = np.asarray(
            forward_returns,
            dtype=float,
        )

        active = positions != 0

        if not np.any(active):
            return np.asarray([], dtype=float)

        gross = (
            positions[active].astype(float)
            * forward_returns[active]
        )

        cost = (
            self._v41_round_trip_cost_bps
            / 10_000.0
        )

        return gross - cost

    def _optimize_direction(
        self,
        *,
        probabilities: np.ndarray,
        classes: np.ndarray,
        forward_returns: np.ndarray,
        direction: str,
    ) -> dict[str, Any]:
        result = super()._optimize_direction(
            probabilities=probabilities,
            classes=classes,
            forward_returns=forward_returns,
            direction=direction,
        )

        if not result["enabled"]:
            result[
                "bootstrap_lower_mean_net_bps"
            ] = None
            return result

        positions = self._direction_positions(
            probabilities=probabilities,
            classes=classes,
            direction=direction,
            threshold=float(result["threshold"]),
        )

        net_event_returns = self._net_event_returns(
            positions=positions,
            forward_returns=forward_returns,
        )

        lower_bound = self.bootstrap_mean_lower_bound(
            net_event_returns
        )
        lower_bound_bps = lower_bound * 10_000.0

        result[
            "bootstrap_lower_mean_net_bps"
        ] = float(lower_bound_bps)
        result[
            "bootstrap_confidence_level"
        ] = self.BOOTSTRAP_CONFIDENCE_LEVEL
        result[
            "bootstrap_repetitions"
        ] = self.BOOTSTRAP_REPETITIONS

        if lower_bound <= 0.0:
            result["enabled"] = False
            result["threshold"] = (
                self.DIRECTION_DISABLED_THRESHOLD
            )
            result["reason"] = (
                "Direction failed V4.3.5 bootstrap "
                "lower-bound expectancy requirement."
            )

        return result
