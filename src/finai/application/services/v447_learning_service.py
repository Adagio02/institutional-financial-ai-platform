from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finai.application.services.v446_learning_service import (
    V446LearningService,
)
from finai.domain.learning.v44_research import (
    selection_penalized_fold_score,
    write_json,
)


class V447LearningService(V446LearningService):
    """
    V4.4.7: selection-adjusted ranking for the V4.4.6 focused search.

    This is still discovery-only. If no candidate qualifies here,
    STOP and do not open the locked-validation block.
    """

    VERSION = "4.4.7"
    LEARNING_ARCHITECTURE = (
        "focused_discovery_selection_"
        "penalized_requalification"
    )

    def __init__(
        self,
        *,
        v447_artifact_directory: str = (
            "artifacts/v447"
        ),
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._v447_artifact_directory = Path(
            v447_artifact_directory
        )
        self._v447_artifact_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _load_v446_payload(
        self,
    ) -> dict[str, Any]:
        path = (
            self._v446_artifact_directory
            / "v446_focused_discovery.json"
        )

        if not path.exists():
            raise FileNotFoundError(
                "V4.4.6 artifact is required: "
                f"{path}"
            )

        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(payload, dict):
            raise RuntimeError(
                "V4.4.6 artifact must contain "
                "a JSON object."
            )

        return payload

    def run_requalification(
        self,
    ) -> dict[str, Any]:
        source = self._load_v446_payload()
        leaderboard = list(
            source.get(
                "leaderboard",
                [],
            )
        )

        trial_count = max(
            1,
            len(leaderboard),
        )

        ranked: list[
            dict[str, Any]
        ] = []

        for item in leaderboard:
            row = dict(item)

            penalty = (
                selection_penalized_fold_score(
                    list(
                        row.get(
                            "fold_returns",
                            [],
                        )
                    ),
                    trial_count=trial_count,
                )
            )

            row.update(
                penalty
            )

            positive_fold_fraction = (
                float(
                    row.get(
                        "positive_fold_fraction",
                        0.0,
                    )
                )
            )
            worst_fold_return = float(
                row.get(
                    "worst_fold_return",
                    0.0,
                )
            )
            net_return = float(
                row.get(
                    "net_return",
                    0.0,
                )
            )
            penalized = float(
                row[
                    "penalized_mean_fold_return"
                ]
            )

            reasons: list[str] = []

            if net_return <= 0.0:
                reasons.append(
                    "non_positive_net_return"
                )

            if (
                positive_fold_fraction
                < self
                ._minimum_positive_fold_fraction
            ):
                reasons.append(
                    "positive_fold_fraction_below_gate"
                )

            if worst_fold_return < -0.05:
                reasons.append(
                    "worst_fold_return_below_-5_percent"
                )

            if penalized <= 0.0:
                reasons.append(
                    "selection_adjusted_return_not_positive"
                )

            row[
                "research_eligible"
            ] = not reasons
            row[
                "rejection_reasons"
            ] = reasons

            ranked.append(row)

        ranked.sort(
            key=lambda item: (
                bool(
                    item[
                        "research_eligible"
                    ]
                ),
                float(
                    item[
                        "penalized_mean_fold_return"
                    ]
                ),
                float(
                    item["net_return"]
                ),
            ),
            reverse=True,
        )

        eligible_count = sum(
            1
            for item in ranked
            if item[
                "research_eligible"
            ]
        )

        payload = {
            "version": self.VERSION,
            "research_only": True,
            "locked_validation_opened": False,
            "final_test_opened": False,
            "trial_count": trial_count,
            "eligible_candidate_count": (
                eligible_count
            ),
            "leaderboard": ranked,
            "next_step": (
                "STOP. No candidate qualifies; "
                "continue discovery research."
                if eligible_count == 0
                else
                "At least one candidate passed "
                "discovery requalification. Freeze "
                "the top eligible candidate in a "
                "new release before opening locked "
                "validation."
            ),
        }

        write_json(
            self._v447_artifact_directory
            / "v447_requalification.json",
            payload,
        )

        return payload
