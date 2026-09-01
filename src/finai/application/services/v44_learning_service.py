from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from finai.application.services.v435_learning_service import (
    V435LearningService,
)
from finai.domain.learning.v44_research import (
    research_configs,
    split_discovery_locked_final,
    write_json,
)


class V44LearningService(V435LearningService):
    """
    V4.4 research-only multi-horizon signal discovery.

    V4.4 searches target definitions inside the discovery partition only.
    It never uses the locked validation or final-test partitions for
    candidate selection and cannot promote a champion.
    """

    VERSION = "4.4"
    LEARNING_ARCHITECTURE = (
        "research_only_multi_horizon_multi_edge_signal_discovery"
    )

    def __init__(
        self,
        *,
        v44_artifact_directory: str = "artifacts/v44",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._v44_artifact_directory = Path(
            v44_artifact_directory
        )
        self._v44_artifact_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _dataset_for_config(
        self,
        *,
        symbol: str,
        interval: str,
        horizon_bars: int,
        edge_bps: float,
    ):
        original_horizon = self._forward_horizon_bars
        original_edge = self._target_minimum_edge_bps

        try:
            self._forward_horizon_bars = int(horizon_bars)
            self._target_minimum_edge_bps = float(edge_bps)

            dataset, rows_loaded = self.build_dataset(
                symbol=symbol,
                interval=interval,
                include_target=True,
            )

            return dataset, rows_loaded
        finally:
            self._forward_horizon_bars = original_horizon
            self._target_minimum_edge_bps = original_edge

    def run_signal_discovery(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> dict[str, Any]:
        normalized_symbol = symbol.strip().upper()
        normalized_interval = interval.strip().lower()

        leaderboard: list[dict[str, Any]] = []

        for config in research_configs():
            dataset, rows_loaded = self._dataset_for_config(
                symbol=normalized_symbol,
                interval=normalized_interval,
                horizon_bars=config.horizon_bars,
                edge_bps=config.edge_bps,
            )

            discovery, _, _ = split_discovery_locked_final(
                dataset
            )

            original_horizon = self._forward_horizon_bars
            original_edge = self._target_minimum_edge_bps

            try:
                self._forward_horizon_bars = (
                    config.horizon_bars
                )
                self._target_minimum_edge_bps = (
                    config.edge_bps
                )

                for model_name, model_template in (
                    self.create_model_templates().items()
                ):
                    evaluation = self.evaluate_model(
                        model_name=model_name,
                        model_template=model_template,
                        research=discovery,
                    )

                    leaderboard.append(
                        {
                            "config": asdict(config),
                            "config_key": config.key,
                            "rows_loaded": int(rows_loaded),
                            "discovery_rows": int(
                                len(discovery)
                            ),
                            "model_name": model_name,
                            "long_threshold": float(
                                evaluation.long_threshold
                            ),
                            "short_threshold": float(
                                evaluation.short_threshold
                            ),
                            "balanced_accuracy": float(
                                evaluation.balanced_accuracy
                            ),
                            "macro_f1": float(
                                evaluation.macro_f1
                            ),
                            "net_return": float(
                                evaluation.net_return
                            ),
                            "trade_count": int(
                                evaluation.trade_count
                            ),
                            "maximum_drawdown": float(
                                evaluation.maximum_drawdown
                            ),
                            "sharpe_like": float(
                                evaluation.sharpe_like
                            ),
                            "positive_fold_fraction": float(
                                evaluation.positive_fold_fraction
                            ),
                            "worst_fold_return": float(
                                evaluation.worst_fold_return
                            ),
                            "fold_returns": [
                                float(fold.net_return)
                                for fold in evaluation.folds
                            ],
                        }
                    )
            finally:
                self._forward_horizon_bars = (
                    original_horizon
                )
                self._target_minimum_edge_bps = (
                    original_edge
                )

        ranked = sorted(
            leaderboard,
            key=lambda item: (
                item["net_return"],
                item["positive_fold_fraction"],
                -item["maximum_drawdown"],
                item["balanced_accuracy"],
            ),
            reverse=True,
        )

        payload = {
            "version": self.VERSION,
            "symbol": normalized_symbol,
            "interval": normalized_interval,
            "research_only": True,
            "locked_validation_used_for_selection": False,
            "final_test_used_for_selection": False,
            "candidate_count": len(ranked),
            "leaderboard": ranked,
        }

        write_json(
            self._v44_artifact_directory
            / "v44_signal_discovery.json",
            payload,
        )

        return payload

    def _promotion_decision(self, **kwargs):
        return (
            False,
            "V4.4 is research-only and cannot promote a champion.",
            0.0,
        )

