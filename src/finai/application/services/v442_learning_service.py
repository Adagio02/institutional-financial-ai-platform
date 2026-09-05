from __future__ import annotations

from typing import Any

from finai.application.services.v441_learning_service import (
    V441LearningService,
)
from finai.domain.learning.v44_research import (
    selection_penalized_fold_score,
    write_json,
)


class V442LearningService(V441LearningService):
    """
    V4.4.2 multiple-testing-aware candidate ranking.

    The release reads only V4.4 discovery results. It adds a conservative
    selection penalty derived from cross-fold dispersion and the total
    number of configurations tried. It does not inspect locked validation
    or final-test data.
    """

    VERSION = "4.4.2"
    LEARNING_ARCHITECTURE = (
        "research_only_selection_penalized_candidate_ranking"
    )

    def run_selection_penalty(
        self,
    ) -> dict[str, Any]:
        source = (
            self._v44_artifact_directory
            / "v44_signal_discovery.json"
        )

        if not source.exists():
            raise FileNotFoundError(
                "Run V4.4 signal discovery before V4.4.2."
            )

        import json

        discovery = json.loads(
            source.read_text(encoding="utf-8")
        )

        candidates = discovery["leaderboard"]
        trial_count = len(candidates)

        output: list[dict[str, Any]] = []

        for candidate in candidates:
            item = dict(candidate)
            penalty = selection_penalized_fold_score(
                list(candidate["fold_returns"]),
                trial_count=trial_count,
            )
            item.update(penalty)

            item["research_eligible"] = bool(
                candidate["net_return"] > 0.0
                and candidate["positive_fold_fraction"]
                >= self._minimum_positive_fold_fraction
                and candidate["worst_fold_return"]
                >= -0.05
                and penalty[
                    "penalized_mean_fold_return"
                ]
                > 0.0
            )

            output.append(item)

        ranked = sorted(
            output,
            key=lambda item: (
                item["research_eligible"],
                item["penalized_mean_fold_return"],
                item["net_return"],
                item["positive_fold_fraction"],
            ),
            reverse=True,
        )

        payload = {
            "version": self.VERSION,
            "research_only": True,
            "trial_count": trial_count,
            "locked_validation_used": False,
            "final_test_used": False,
            "leaderboard": ranked,
        }

        write_json(
            self._v44_artifact_directory
            / "v442_selection_penalized.json",
            payload,
        )

        return payload

