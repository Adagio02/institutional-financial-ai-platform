from __future__ import annotations

from copy import deepcopy
from typing import Any

import numpy as np

from finai.application.services.v44_learning_service import (
    V44LearningService,
)
from finai.domain.learning.v41_features import (
    V41_FEATURE_COLUMNS,
)
from finai.domain.learning.v44_research import (
    FEATURE_FAMILIES,
    split_discovery_locked_final,
    write_json,
)


class V441LearningService(V44LearningService):
    """
    V4.4.1 feature-family ablation.

    Feature-family ablation is performed only on the discovery partition.
    Ablated columns are replaced by discovery medians, preserving the
    estimator input schema while removing time-varying information from
    that family.
    """

    VERSION = "4.4.1"
    LEARNING_ARCHITECTURE = (
        "research_only_feature_family_ablation_candidate_leaderboard"
    )

    def _ablated_frame(
        self,
        frame,
        *,
        family: str,
    ):
        result = frame.copy()

        columns = [
            column
            for column in FEATURE_FAMILIES[family]
            if column in result.columns
        ]

        for column in columns:
            median = float(
                np.nanmedian(
                    result[column].to_numpy(dtype=float)
                )
            )
            if not np.isfinite(median):
                median = 0.0
            result[column] = median

        return result

    def run_feature_ablation(
        self,
        *,
        symbol: str,
        interval: str,
        horizon_bars: int = 15,
        edge_bps: float = 3.0,
    ) -> dict[str, Any]:
        dataset, _ = self._dataset_for_config(
            symbol=symbol.strip().upper(),
            interval=interval.strip().lower(),
            horizon_bars=horizon_bars,
            edge_bps=edge_bps,
        )

        discovery, _, _ = split_discovery_locked_final(
            dataset
        )

        original_horizon = self._forward_horizon_bars
        original_edge = self._target_minimum_edge_bps

        rows: list[dict[str, Any]] = []

        try:
            self._forward_horizon_bars = int(
                horizon_bars
            )
            self._target_minimum_edge_bps = float(
                edge_bps
            )

            variants = ["baseline"] + sorted(
                FEATURE_FAMILIES
            )

            for variant in variants:
                frame = (
                    discovery
                    if variant == "baseline"
                    else self._ablated_frame(
                        discovery,
                        family=variant,
                    )
                )

                for model_name, model_template in (
                    self.create_model_templates().items()
                ):
                    evaluation = self.evaluate_model(
                        model_name=model_name,
                        model_template=model_template,
                        research=frame,
                    )

                    rows.append(
                        {
                            "variant": variant,
                            "model_name": model_name,
                            "horizon_bars": horizon_bars,
                            "edge_bps": edge_bps,
                            "net_return": float(
                                evaluation.net_return
                            ),
                            "balanced_accuracy": float(
                                evaluation.balanced_accuracy
                            ),
                            "macro_f1": float(
                                evaluation.macro_f1
                            ),
                            "trade_count": int(
                                evaluation.trade_count
                            ),
                            "maximum_drawdown": float(
                                evaluation.maximum_drawdown
                            ),
                            "positive_fold_fraction": float(
                                evaluation.positive_fold_fraction
                            ),
                            "worst_fold_return": float(
                                evaluation.worst_fold_return
                            ),
                        }
                    )
        finally:
            self._forward_horizon_bars = (
                original_horizon
            )
            self._target_minimum_edge_bps = (
                original_edge
            )

        payload = {
            "version": self.VERSION,
            "research_only": True,
            "rows": sorted(
                rows,
                key=lambda item: item["net_return"],
                reverse=True,
            ),
        }

        write_json(
            self._v44_artifact_directory
            / "v441_feature_ablation.json",
            payload,
        )

        return payload

