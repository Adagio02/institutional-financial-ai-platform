from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finai.application.services.v46_learning_service import (
    V46LearningService,
)
from finai.domain.learning.v44_research import write_json
from finai.domain.learning.v46_research import (
    selection_penalty,
)


class V461LearningService(V46LearningService):
    VERSION = "4.6.1"
    LEARNING_ARCHITECTURE = (
        "event_discovery_selection_"
        "adjusted_shortlist"
    )

    def __init__(
        self,
        *,
        v461_artifact_directory: str = "artifacts/v461",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._v461_artifact_directory = Path(
            v461_artifact_directory
        )
        self._v461_artifact_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def run_shortlist(
        self,
    ) -> dict[str, Any]:
        path = (
            self._v46_artifact_directory
            / "v46_event_discovery.json"
        )
        if not path.exists():
            raise FileNotFoundError(
                "Run V4.6 first."
            )

        source = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
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

        scored = []

        for item in leaderboard:
            row = dict(item)
            row.update(
                selection_penalty(
                    list(
                        row.get(
                            "fold_returns",
                            [],
                        )
                    ),
                    trial_count=trial_count,
                )
            )

            reasons = []

            if float(
                row.get(
                    "net_return",
                    0.0,
                )
            ) <= 0.0:
                reasons.append(
                    "non_positive_net_return"
                )

            if float(
                row.get(
                    "positive_fold_fraction",
                    0.0,
                )
            ) < 0.40:
                reasons.append(
                    "less_than_two_positive_folds"
                )

            if int(
                row.get(
                    "trade_count",
                    0,
                )
            ) < 50:
                reasons.append(
                    "insufficient_research_trades"
                )

            if float(
                row.get(
                    "penalized_mean_fold_return",
                    0.0,
                )
            ) <= 0.0:
                reasons.append(
                    "selection_adjusted_return_not_positive"
                )

            row[
                "shortlist_eligible"
            ] = not reasons
            row[
                "shortlist_failure_reasons"
            ] = reasons

            scored.append(row)

        scored.sort(
            key=lambda item: (
                bool(
                    item[
                        "shortlist_eligible"
                    ]
                ),
                float(
                    item[
                        "penalized_mean_fold_return"
                    ]
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

        shortlist = [
            item
            for item in scored
            if item[
                "shortlist_eligible"
            ]
        ][:8]

        payload = {
            "version": self.VERSION,
            "research_only": True,
            "locked_validation_opened": False,
            "final_test_opened": False,
            "source_trial_count": trial_count,
            "shortlist_count": len(
                shortlist
            ),
            "shortlist": shortlist,
            "leaderboard": scored,
            "next_step": (
                "run V4.6.2 focused model refinement"
                if shortlist
                else
                "stop: event formulation produced no robust shortlist"
            ),
        }

        write_json(
            self._v461_artifact_directory
            / "v461_shortlist.json",
            payload,
        )

        return payload
