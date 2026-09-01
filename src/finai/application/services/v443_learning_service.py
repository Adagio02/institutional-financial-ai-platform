from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sklearn.base import clone

from finai.application.services.v442_learning_service import (
    V442LearningService,
)
from finai.domain.learning.v41_features import (
    V41_FEATURE_COLUMNS,
)
from finai.domain.learning.v44_research import (
    freeze_payload,
    purge_and_embargo,
    split_discovery_locked_final,
    write_json,
)


class V443LearningService(V442LearningService):
    """
    V4.4.3 candidate freeze + locked research validation.

    Candidate selection comes exclusively from V4.4.2 discovery results.
    The selected candidate is hashed before the locked validation block
    is evaluated. The final test remains untouched.
    """

    VERSION = "4.4.3"
    LEARNING_ARCHITECTURE = (
        "candidate_freeze_locked_research_validation"
    )

    def freeze_best_candidate(
        self,
    ) -> dict[str, Any]:
        source = (
            self._v44_artifact_directory
            / "v442_selection_penalized.json"
        )

        if not source.exists():
            raise FileNotFoundError(
                "Run V4.4.2 before freezing a candidate."
            )

        payload = json.loads(
            source.read_text(encoding="utf-8")
        )

        eligible = [
            item
            for item in payload["leaderboard"]
            if item["research_eligible"]
        ]

        if not eligible:
            result = {
                "version": self.VERSION,
                "status": "no_qualified_research_candidate",
                "frozen": False,
            }
            write_json(
                self._v44_artifact_directory
                / "v443_frozen_candidate.json",
                result,
            )
            return result

        selected = eligible[0]

        candidate = {
            "config": selected["config"],
            "config_key": selected["config_key"],
            "model_name": selected["model_name"],
            "long_threshold": selected[
                "long_threshold"
            ],
            "short_threshold": selected[
                "short_threshold"
            ],
            "discovery_net_return": selected[
                "net_return"
            ],
            "selection_penalized_mean_fold_return": (
                selected[
                    "penalized_mean_fold_return"
                ]
            ),
        }

        frozen = freeze_payload(candidate)
        result = {
            "version": self.VERSION,
            "status": "frozen",
            "frozen": True,
            **frozen,
        }

        write_json(
            self._v44_artifact_directory
            / "v443_frozen_candidate.json",
            result,
        )

        return result

    def run_locked_validation(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> dict[str, Any]:
        frozen_path = (
            self._v44_artifact_directory
            / "v443_frozen_candidate.json"
        )

        if not frozen_path.exists():
            raise FileNotFoundError(
                "Freeze the V4.4.3 candidate first."
            )

        frozen = json.loads(
            frozen_path.read_text(encoding="utf-8")
        )

        if not frozen.get("frozen"):
            return {
                "version": self.VERSION,
                "status": "not_run_no_frozen_candidate",
            }

        candidate = frozen["candidate"]
        config = candidate["config"]

        dataset, _ = self._dataset_for_config(
            symbol=symbol.strip().upper(),
            interval=interval.strip().lower(),
            horizon_bars=int(
                config["horizon_bars"]
            ),
            edge_bps=float(
                config["edge_bps"]
            ),
        )

        discovery, locked, _ = (
            split_discovery_locked_final(dataset)
        )

        train, validation = purge_and_embargo(
            discovery,
            locked,
            horizon_bars=int(
                config["horizon_bars"]
            ),
        )

        model_template = (
            self.create_model_templates()[
                candidate["model_name"]
            ]
        )
        model = clone(model_template)

        model.fit(
            train[V41_FEATURE_COLUMNS],
            train["target"],
        )

        original_horizon = self._forward_horizon_bars
        original_edge = self._target_minimum_edge_bps

        try:
            self._forward_horizon_bars = int(
                config["horizon_bars"]
            )
            self._target_minimum_edge_bps = float(
                config["edge_bps"]
            )

            (
                balanced_accuracy,
                macro_f1,
                backtest,
            ) = self.evaluate_holdout(
                model=model,
                holdout=validation,
                long_threshold=float(
                    candidate["long_threshold"]
                ),
                short_threshold=float(
                    candidate["short_threshold"]
                ),
            )
        finally:
            self._forward_horizon_bars = (
                original_horizon
            )
            self._target_minimum_edge_bps = (
                original_edge
            )

        result = {
            "version": self.VERSION,
            "status": "completed",
            "candidate_sha256": frozen["sha256"],
            "final_test_touched": False,
            "rows": int(len(validation)),
            "balanced_accuracy": float(
                balanced_accuracy
            ),
            "macro_f1": float(macro_f1),
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
            "locked_qualified": bool(
                backtest.net_return > 0.0
                and backtest.trade_count
                >= self._minimum_trades
                and backtest.maximum_drawdown
                <= self._maximum_holdout_drawdown
                and balanced_accuracy
                >= self._minimum_balanced_accuracy
                and macro_f1
                >= self._minimum_macro_f1
            ),
        }

        write_json(
            self._v44_artifact_directory
            / "v443_locked_validation.json",
            result,
        )

        return result

