from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finai.application.services.v461_learning_service import (
    V461LearningService,
)
from finai.domain.learning.v44_research import (
    split_discovery_locked_final,
    write_json,
)
from finai.domain.learning.v46_models import (
    FOCUSED_MODEL_CONFIGS,
)


class V462LearningService(V461LearningService):
    VERSION = "4.6.2"
    LEARNING_ARCHITECTURE = (
        "focused_event_meta_model_"
        "refinement_discovery_only"
    )

    def __init__(
        self,
        *,
        v462_artifact_directory: str = "artifacts/v462",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._v462_artifact_directory = Path(
            v462_artifact_directory
        )
        self._v462_artifact_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def run_focused_refinement(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> dict[str, Any]:
        source_path = (
            self._v461_artifact_directory
            / "v461_shortlist.json"
        )

        if not source_path.exists():
            raise FileNotFoundError(
                "Run V4.6.1 first."
            )

        source = json.loads(
            source_path.read_text(
                encoding="utf-8"
            )
        )
        shortlist = list(
            source.get(
                "shortlist",
                [],
            )
        )

        if not shortlist:
            payload = {
                "version": self.VERSION,
                "status": (
                    "no_shortlist_candidate"
                ),
                "research_only": True,
                "locked_validation_opened": False,
                "final_test_opened": False,
                "leaderboard": [],
            }

            write_json(
                self._v462_artifact_directory
                / "v462_focused_refinement.json",
                payload,
            )

            return payload

        pairs = []
        seen = set()

        for item in shortlist:
            key = (
                int(
                    item["horizon_bars"]
                ),
                str(
                    item["event_family"]
                ),
            )

            if key in seen:
                continue

            seen.add(key)
            pairs.append(key)

        leaderboard = []

        for horizon, family in pairs:
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

            for (
                model_name,
                model_config,
            ) in FOCUSED_MODEL_CONFIGS.items():

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
                ] = int(
                    rows_loaded
                )

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
            ),
            reverse=True,
        )

        payload = {
            "version": self.VERSION,
            "research_only": True,
            "locked_validation_opened": False,
            "final_test_opened": False,
            "governance_weakened": False,
            "focused_pair_count": len(
                pairs
            ),
            "trial_count": len(
                leaderboard
            ),
            "leaderboard": leaderboard,
        }

        write_json(
            self._v462_artifact_directory
            / "v462_focused_refinement.json",
            payload,
        )

        return payload
