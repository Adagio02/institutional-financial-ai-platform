from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from finai.application.services.v432_learning_service import (
    V432LearningService,
)


class V433LearningService(V432LearningService):
    """
    V4.3.3 regime-aware directional stability.

    Candidates that already satisfy V4.3.2 must also demonstrate that
    their signal is not concentrated in only one observable market
    regime. Regimes are derived only from contemporaneous feature rows:
    trend_strength and market_volatility. No future return is used to
    assign a regime.
    """

    VERSION = "4.3.3"
    LEARNING_ARCHITECTURE = (
        "regime_aware_sample_aware_directional_"
        "confidence_abstention_ensemble"
    )

    REGIME_MINIMUM_TRADES = 8
    MINIMUM_POSITIVE_REGIME_FRACTION = 0.50

    @staticmethod
    def _regime_labels(
        calibration: pd.DataFrame,
    ) -> np.ndarray:
        trend = calibration["trend_strength"].to_numpy(
            dtype=float
        )
        volatility = calibration["market_volatility"].to_numpy(
            dtype=float
        )

        finite_volatility = volatility[
            np.isfinite(volatility)
        ]

        if len(finite_volatility) == 0:
            volatility_cut = 0.0
        else:
            volatility_cut = float(
                np.nanmedian(finite_volatility)
            )

        trend_label = np.where(
            trend >= 0.0,
            "trend_up",
            "trend_down",
        )
        volatility_label = np.where(
            volatility >= volatility_cut,
            "vol_high",
            "vol_low",
        )

        return np.char.add(
            np.char.add(
                trend_label.astype(str),
                "__",
            ),
            volatility_label.astype(str),
        )

    def _regime_diagnostics(
        self,
        *,
        positions: np.ndarray,
        forward_returns: np.ndarray,
        regime_labels: np.ndarray,
    ) -> dict[str, Any]:
        output: list[dict[str, Any]] = []

        for regime in sorted(set(regime_labels.tolist())):
            mask = regime_labels == regime

            backtest = self.simulate(
                positions=positions[mask],
                forward_returns=forward_returns[mask],
            )

            output.append(
                {
                    "regime": regime,
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
            )

        eligible = [
            item
            for item in output
            if (
                item["trade_count"]
                >= self.REGIME_MINIMUM_TRADES
            )
        ]

        if eligible:
            positive_fraction = float(
                np.mean(
                    [
                        item["net_return"] > 0.0
                        for item in eligible
                    ]
                )
            )
        else:
            positive_fraction = 0.0

        return {
            "regimes": output,
            "eligible_regime_count": len(eligible),
            "positive_regime_fraction": positive_fraction,
        }

    def _optimize_thresholds(
        self,
        *,
        model: Any,
        calibration: pd.DataFrame,
    ):
        probabilities = model.predict_proba(
            calibration[self.feature_columns]
        )
        forward_returns = calibration[
            "forward_return"
        ].to_numpy(dtype=float)
        regime_labels = self._regime_labels(calibration)

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

        for result in (long_result, short_result):
            if not result["enabled"]:
                result["regime_diagnostics"] = {
                    "regimes": [],
                    "eligible_regime_count": 0,
                    "positive_regime_fraction": 0.0,
                }
                continue

            positions = self._direction_positions(
                probabilities=probabilities,
                classes=model.classes_,
                direction=result["direction"],
                threshold=float(result["threshold"]),
            )

            regime_diagnostics = self._regime_diagnostics(
                positions=positions,
                forward_returns=forward_returns,
                regime_labels=regime_labels,
            )
            result["regime_diagnostics"] = (
                regime_diagnostics
            )

            if (
                regime_diagnostics[
                    "positive_regime_fraction"
                ]
                < self.MINIMUM_POSITIVE_REGIME_FRACTION
            ):
                result["enabled"] = False
                result["threshold"] = (
                    self.DIRECTION_DISABLED_THRESHOLD
                )
                result["reason"] = (
                    "Direction failed V4.3.3 observable-regime "
                    "stability."
                )

        long_threshold = float(long_result["threshold"])
        short_threshold = float(short_result["threshold"])

        positions = self.positions_from_probabilities(
            probabilities=probabilities,
            classes=model.classes_,
            long_threshold=long_threshold,
            short_threshold=short_threshold,
        )
        backtest = self.simulate(
            positions=positions,
            forward_returns=forward_returns,
        )

        self._v43_threshold_diagnostics["latest"] = {
            "executable": bool(
                long_result["enabled"]
                or short_result["enabled"]
            ),
            "long_enabled": bool(
                long_result["enabled"]
            ),
            "short_enabled": bool(
                short_result["enabled"]
            ),
            "selected_long_threshold": long_threshold,
            "selected_short_threshold": short_threshold,
            "long": long_result,
            "short": short_result,
            "combined": {
                "trade_count": int(backtest.trade_count),
                "net_return": float(backtest.net_return),
                "maximum_drawdown": float(
                    backtest.maximum_drawdown
                ),
                "sharpe_like": float(
                    backtest.sharpe_like
                ),
            },
        }

        return (
            long_threshold,
            short_threshold,
            backtest,
        )
