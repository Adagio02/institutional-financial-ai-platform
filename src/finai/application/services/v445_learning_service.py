from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finai.application.services.v442_learning_service import (
    V442LearningService,
)
from finai.domain.learning.v44_research import (
    write_json,
)
from finai.domain.learning.v445_research import (
    candidate_failure_reasons,
    select_focused_candidates,
)


class V445LearningService(V442LearningService):
    """
    V4.4.5: discovery-only stability diagnostics.

    This release does NOT open locked validation or final-test data.
    It explains why V4.4.2 candidates failed and creates a focused,
    discovery-only shortlist for the next research experiment.
    """

    VERSION = "4.4.5"
    LEARNING_ARCHITECTURE = (
        "discovery_only_stability_diagnostics_"
        "and_focused_candidate_selection"
    )

    def __init__(
        self,
        *,
        v445_artifact_directory: str = (
            "artifacts/v445"
        ),
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._v445_artifact_directory = Path(
            v445_artifact_directory
        )
        self._v445_artifact_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _load_v442_payload(
        self,
    ) -> dict[str, Any]:
        path = (
            self._v44_artifact_directory
            / "v442_selection_penalized.json"
        )

        if not path.exists():
            raise FileNotFoundError(
                "V4.4.2 artifact is required: "
                f"{path}"
            )

        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(payload, dict):
            raise RuntimeError(
                "V4.4.2 artifact must contain "
                "a JSON object."
            )

        return payload

    def run_stability_diagnostics(
        self,
    ) -> dict[str, Any]:
        source = self._load_v442_payload()
        leaderboard = list(
            source.get(
                "leaderboard",
                [],
            )
        )

        focused = (
            select_focused_candidates(
                leaderboard,
                maximum_candidates=8,
                minimum_trades=50,
            )
        )

        rows: list[dict[str, Any]] = []

        for item in leaderboard:
            row = dict(item)
            row[
                "v445_failure_reasons"
            ] = candidate_failure_reasons(
                row
            )
            rows.append(row)

        payload = {
            "version": self.VERSION,
            "research_only": True,
            "locked_validation_opened": False,
            "final_test_opened": False,
            "source_version": (
                source.get("version")
            ),
            "source_candidate_count": len(
                leaderboard
            ),
            "focused_candidate_count": len(
                focused
            ),
            "focused_candidates": [
                {
                    "config_key": item.config_key,
                    "model_name": item.model_name,
                    "horizon_bars": (
                        item.horizon_bars
                    ),
                    "edge_bps": (
                        item.edge_bps
                    ),
                    "source_net_return": (
                        item.source_net_return
                    ),
                    "source_trade_count": (
                        item.source_trade_count
                    ),
                    "source_positive_fold_fraction": (
                        item
                        .source_positive_fold_fraction
                    ),
                }
                for item in focused
            ],
            "diagnostic_leaderboard": rows,
            "next_step": (
                "Run V4.4.6 focused recent-window "
                "discovery. Do not open locked "
                "validation."
            ),
        }

        write_json(
            self._v445_artifact_directory
            / "v445_stability_diagnostics.json",
            payload,
        )

        return payload
