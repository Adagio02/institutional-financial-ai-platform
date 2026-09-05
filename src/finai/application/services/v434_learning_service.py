from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from finai.application.services.v433_learning_service import (
    V433LearningService,
)
from finai.domain.learning.v43_research import (
    BUY,
    HOLD,
    SELL,
    probability_columns,
)


class V434LearningService(V433LearningService):
    """
    V4.3.4 probability-margin abstention.

    In addition to absolute confidence, a directional prediction must
    beat both HOLD and the opposite direction by a configurable margin.
    The margin is selected only from the calibration window.
    """

    VERSION = "4.3.4"
    LEARNING_ARCHITECTURE = (
        "probability_margin_regime_aware_sample_aware_"
        "directional_confidence_abstention_ensemble"
    )

    PROBABILITY_MARGIN_GRID = (
        0.00,
        0.025,
        0.05,
        0.075,
        0.10,
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._active_probability_margin = 0.0

    @classmethod
    def positions_with_margin(
        cls,
        *,
        probabilities: np.ndarray,
        classes: np.ndarray,
        long_threshold: float,
        short_threshold: float,
        margin: float,
    ) -> np.ndarray:
        short_probability, hold_probability, long_probability = (
            probability_columns(
                probabilities=probabilities,
                classes=classes,
            )
        )

        positions = np.full(
            len(probabilities),
            HOLD,
            dtype=int,
        )

        margin = max(0.0, float(margin))

        if float(long_threshold) < 1.0:
            threshold = max(
                float(long_threshold),
                cls.MINIMUM_SIGNAL_PROBABILITY,
            )
            long_mask = (
                (long_probability >= threshold)
                & (
                    long_probability - short_probability
                    >= margin
                )
                & (
                    long_probability - hold_probability
                    >= margin
                )
            )
            positions[long_mask] = BUY

        if float(short_threshold) < 1.0:
            threshold = max(
                float(short_threshold),
                cls.MINIMUM_SIGNAL_PROBABILITY,
            )
            short_mask = (
                (short_probability >= threshold)
                & (
                    short_probability - long_probability
                    >= margin
                )
                & (
                    short_probability - hold_probability
                    >= margin
                )
            )
            positions[short_mask] = SELL

        return positions

    def positions_from_probabilities(
        self,
        *,
        probabilities: np.ndarray,
        classes: np.ndarray,
        long_threshold: float,
        short_threshold: float,
    ) -> np.ndarray:
        return self.positions_with_margin(
            probabilities=probabilities,
            classes=classes,
            long_threshold=long_threshold,
            short_threshold=short_threshold,
            margin=self._active_probability_margin,
        )

    def _optimize_thresholds(
        self,
        *,
        model: Any,
        calibration: pd.DataFrame,
    ):
        original_margin = self._active_probability_margin

        best = None
        best_score = float("-inf")
        margin_diagnostics: list[dict[str, Any]] = []

        try:
            for margin in self.PROBABILITY_MARGIN_GRID:
                self._active_probability_margin = float(
                    margin
                )

                (
                    long_threshold,
                    short_threshold,
                    backtest,
                ) = super()._optimize_thresholds(
                    model=model,
                    calibration=calibration,
                )

                diagnostic = {
                    "margin": float(margin),
                    "long_threshold": float(
                        long_threshold
                    ),
                    "short_threshold": float(
                        short_threshold
                    ),
                    "trade_count": int(
                        backtest.trade_count
                    ),
                    "net_return": float(
                        backtest.net_return
                    ),
                    "maximum_drawdown": float(
                        backtest.maximum_drawdown
                    ),
                    "sharpe_like": float(
                        backtest.sharpe_like
                    ),
                }
                margin_diagnostics.append(diagnostic)

                if backtest.trade_count <= 0:
                    continue

                score = (
                    float(backtest.net_return)
                    - float(
                        backtest.maximum_drawdown
                    )
                    * 0.50
                    + float(backtest.sharpe_like)
                    * 0.02
                )

                if score > best_score:
                    best_score = score
                    best = (
                        float(margin),
                        float(long_threshold),
                        float(short_threshold),
                        backtest,
                    )

            if best is None:
                self._active_probability_margin = 0.0
                return super()._optimize_thresholds(
                    model=model,
                    calibration=calibration,
                )

            (
                selected_margin,
                long_threshold,
                short_threshold,
                backtest,
            ) = best

            self._active_probability_margin = (
                selected_margin
            )

            latest = self._v43_threshold_diagnostics.get(
                "latest",
                {},
            )
            latest[
                "selected_probability_margin"
            ] = selected_margin
            latest[
                "probability_margin_diagnostics"
            ] = margin_diagnostics
            self._v43_threshold_diagnostics[
                "latest"
            ] = latest

            return (
                long_threshold,
                short_threshold,
                backtest,
            )
        except Exception:
            self._active_probability_margin = original_margin
            raise
