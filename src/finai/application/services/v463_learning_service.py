from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finai.application.services.v462_learning_service import (
    V462LearningService,
)
from finai.domain.learning.v44_research import write_json
from finai.domain.learning.v46_research import (
    selection_penalty,
)


class V463LearningService(V462LearningService):
    VERSION = "4.6.3"
    LEARNING_ARCHITECTURE = (
        "event_meta_selection_adjusted_"
        "requalification"
    )

    def __init__(
        self,
        *,
        v463_artifact_directory: str = "artifacts/v463",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._v463_artifact_directory = Path(
            v463_artifact_directory
        )
        self._v463_artifact_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def run_requalification(
        self,
    ) -> dict[str, Any]:
        path = (
            self._v462_artifact_directory
            / "v462_focused_refinement.json"
        )

        if not path.exists():
            raise FileNotFoundError(
                "Run V4.6.2 first."
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

        ranked = []

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
            ) < float(
                self._minimum_positive_fold_fraction
            ):
                reasons.append(
                    "positive_fold_fraction_below_existing_gate"
                )

            if int(
                row.get(
                    "trade_count",
                    0,
                )
            ) < int(
                self._minimum_trades
            ):
                reasons.append(
                    "trade_count_below_existing_gate"
                )

            if float(
                row.get(
                    "worst_fold_return",
                    0.0,
                )
            ) < -0.05:
                reasons.append(
                    "worst_fold_below_-5_percent"
                )

            if float(
                row.get(
                    "penalized_mean_fold_return",
                    0.0,
                )
            ) <= 0.0:
                reasons.append(
                    "selection_adjusted_expectancy_not_positive"
                )

            if float(
                row.get(
                    "meta_balanced_accuracy",
                    0.0,
                )
            ) < 0.52:
                reasons.append(
                    "meta_balanced_accuracy_below_0p52"
                )

            row[
                "research_eligible"
            ] = not reasons
            row[
                "failure_reasons"
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
                    item.get(
                        "net_return",
                        0.0,
                    )
                ),
            ),
            reverse=True,
        )

        eligible = [
            item
            for item in ranked
            if item[
                "research_eligible"
            ]
        ]

        payload = {
            "version": self.VERSION,
            "research_only": True,
            "locked_validation_opened": False,
            "final_test_opened": False,
            "governance_weakened": False,
            "trial_count": trial_count,
            "eligible_candidate_count": len(
                eligible
            ),
            "leaderboard": ranked,
            "next_step": (
                "run V4.6.4 freeze"
                if eligible
                else
                "stop; do not open locked validation"
            ),
        }

        write_json(
            self._v463_artifact_directory
            / "v463_requalification.json",
            payload,
        )

        return payload
