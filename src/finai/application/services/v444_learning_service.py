from __future__ import annotations

import json
from typing import Any

from sklearn.base import clone

from finai.application.services.v443_learning_service import (
    V443LearningService,
)
from finai.domain.learning.v41_features import (
    V41_FEATURE_COLUMNS,
)
from finai.domain.learning.v44_research import (
    purge_and_embargo,
    split_discovery_locked_final,
    verify_frozen_payload,
    write_json,
)


class V444LearningService(V443LearningService):
    """
    V4.4.4 one-shot untouched final test.

    The frozen candidate cannot be altered here. The final chronological
    block is opened only after the V4.4.3 locked validation qualifies.
    V4.4.4 reports historical qualification only; champion promotion is
    intentionally deferred to prospective shadow governance.
    """

    VERSION = "4.4.4"
    LEARNING_ARCHITECTURE = (
        "one_shot_untouched_final_test_before_shadow"
    )

    def run_final_test(
        self,
        *,
        symbol: str,
        interval: str,
    ) -> dict[str, Any]:
        frozen_path = (
            self._v44_artifact_directory
            / "v443_frozen_candidate.json"
        )
        locked_path = (
            self._v44_artifact_directory
            / "v443_locked_validation.json"
        )
        final_path = (
            self._v44_artifact_directory
            / "v444_final_test.json"
        )

        if final_path.exists():
            raise RuntimeError(
                "V4.4.4 final test already exists. "
                "Do not repeatedly reopen the final test."
            )

        if not frozen_path.exists():
            raise FileNotFoundError(
                "Missing V4.4.3 frozen candidate."
            )
        if not locked_path.exists():
            raise FileNotFoundError(
                "Missing V4.4.3 locked validation."
            )

        frozen = json.loads(
            frozen_path.read_text(encoding="utf-8")
        )
        locked = json.loads(
            locked_path.read_text(encoding="utf-8")
        )

        if not verify_frozen_payload(frozen):
            raise RuntimeError(
                "Frozen candidate hash verification failed."
            )

        if not locked.get("locked_qualified"):
            result = {
                "version": self.VERSION,
                "status": (
                    "not_run_locked_validation_failed"
                ),
                "final_test_opened": False,
                "champion_promoted": False,
            }
            write_json(final_path, result)
            return result

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

        discovery, locked_frame, final = (
            split_discovery_locked_final(dataset)
        )

        pre_final = __import__("pandas").concat(
            [discovery, locked_frame],
            ignore_index=True,
        )

        train, final_eval = purge_and_embargo(
            pre_final,
            final,
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
                holdout=final_eval,
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

        historical_qualified = bool(
            balanced_accuracy
            >= self._minimum_balanced_accuracy
            and macro_f1
            >= self._minimum_macro_f1
            and backtest.net_return
            > self._minimum_net_return
            and backtest.trade_count
            >= self._minimum_trades
            and backtest.maximum_drawdown
            <= self._maximum_holdout_drawdown
        )

        result = {
            "version": self.VERSION,
            "status": "completed",
            "candidate_sha256": frozen["sha256"],
            "final_test_opened": True,
            "one_shot": True,
            "rows": int(len(final_eval)),
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
            "historical_qualified": (
                historical_qualified
            ),
            "champion_promoted": False,
            "next_step": (
                "prospective shadow validation"
                if historical_qualified
                else "return to research with a new final period"
            ),
        }

        write_json(final_path, result)

        return result

