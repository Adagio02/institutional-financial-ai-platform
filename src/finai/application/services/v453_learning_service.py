from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finai.application.services.v452_learning_service import (
    V452LearningService,
)
from finai.domain.learning.v44_research import (
    write_json,
)
from finai.domain.learning.v45_research import (
    research_eligible,
    selection_penalty,
)


class V453LearningService(V452LearningService):
    VERSION = "4.5.3"
    LEARNING_ARCHITECTURE = (
        "selection_adjusted_signal_"
        "requalification_discovery_only"
    )

    def __init__(
        self,
        *,
        v453_artifact_directory: str = (
            "artifacts/v453"
        ),
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._v453_artifact_directory = Path(
            v453_artifact_directory
        )
        self._v453_artifact_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _load_directional(
        self,
    ) -> dict[str, Any]:
        path = (
            self._v452_artifact_directory
            / "v452_directional_research.json"
        )
        if not path.exists():
            raise FileNotFoundError(
                "Run V4.5.2 first: "
                f"{path}"
            )
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    def run_requalification(
        self,
    ) -> dict[str, Any]:
        source = self._load_directional()
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
            candidate = dict(item)
            penalty = selection_penalty(
                list(
                    candidate.get(
                        "fold_returns",
                        [],
                    )
                ),
                trial_count=trial_count,
            )
            candidate.update(penalty)

            eligible, reasons = (
                research_eligible(
                    candidate,
                    minimum_positive_fold_fraction=(
                        self
                        ._minimum_positive_fold_fraction
                    ),
                    minimum_trades=(
                        self._minimum_trades
                    ),
                )
            )
            candidate[
                "research_eligible"
            ] = bool(eligible)
            candidate[
                "failure_reasons"
            ] = reasons
            ranked.append(candidate)

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
            "governance_weakened": False,
            "trial_count": trial_count,
            "eligible_candidate_count": (
                eligible_count
            ),
            "status": (
                "qualified_research_candidate_exists"
                if eligible_count > 0
                else "no_qualified_research_candidate"
            ),
            "leaderboard": ranked,
            "next_step": (
                "freeze one discovery-qualified candidate "
                "before locked validation"
                if eligible_count > 0
                else "stop; do not open locked validation"
            ),
        }
        write_json(
            self._v453_artifact_directory
            / "v453_requalification.json",
            payload,
        )
        return payload
