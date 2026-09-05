from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finai.application.services.v463_learning_service import (
    V463LearningService,
)
from finai.domain.learning.v44_research import write_json
from finai.domain.learning.v46_research import (
    candidate_hash,
)


class V464LearningService(V463LearningService):
    VERSION = "4.6.4"
    LEARNING_ARCHITECTURE = (
        "frozen_event_meta_candidate"
    )

    def __init__(
        self,
        *,
        v464_artifact_directory: str = "artifacts/v464",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._v464_artifact_directory = Path(
            v464_artifact_directory
        )
        self._v464_artifact_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def freeze_candidate(
        self,
    ) -> dict[str, Any]:
        source_path = (
            self._v463_artifact_directory
            / "v463_requalification.json"
        )

        if not source_path.exists():
            raise FileNotFoundError(
                "Run V4.6.3 first."
            )

        source = json.loads(
            source_path.read_text(
                encoding="utf-8"
            )
        )

        eligible = [
            item
            for item in source.get(
                "leaderboard",
                [],
            )
            if item.get(
                "research_eligible"
            )
        ]

        if not eligible:
            payload = {
                "version": self.VERSION,
                "frozen": False,
                "status": (
                    "no_qualified_research_candidate"
                ),
                "locked_validation_opened": False,
            }

        else:
            winner = dict(
                eligible[0]
            )

            candidate = {
                "horizon_bars": int(
                    winner[
                        "horizon_bars"
                    ]
                ),
                "event_family": str(
                    winner[
                        "event_family"
                    ]
                ),
                "model_name": str(
                    winner[
                        "model_name"
                    ]
                ),
                "model_config": dict(
                    winner[
                        "model_config"
                    ]
                ),
                "selected_threshold": float(
                    winner[
                        "selected_threshold"
                    ]
                ),
            }

            payload = {
                "version": self.VERSION,
                "frozen": True,
                "candidate": candidate,
                "candidate_sha256": (
                    candidate_hash(
                        candidate
                    )
                ),
                "locked_validation_opened": False,
                "next_step": (
                    "V4.6.5 locked validation"
                ),
            }

        write_json(
            self._v464_artifact_directory
            / "v464_frozen_candidate.json",
            payload,
        )

        return payload
