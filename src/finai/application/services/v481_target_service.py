from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finai.domain.learning.v481_targets import add_neutral_targets, target_summary
from finai.domain.learning.v48_storage import read_research_frame, write_research_frame


class V481TargetService:
    VERSION = "4.8.1"

    def __init__(
        self,
        *,
        source_path: str = "artifacts/v48/v48_feature_panel",
        artifact_directory: str = "artifacts/v481",
    ) -> None:
        self._source_path = Path(source_path)
        self._artifact_directory = Path(artifact_directory)

    def run(self) -> dict[str, Any]:
        try:
            frame = read_research_frame(self._source_path)
        except FileNotFoundError as exc:
            raise FileNotFoundError("Run V4.8 before V4.8.1.") from exc
        targeted = add_neutral_targets(frame)
        self._artifact_directory.mkdir(parents=True, exist_ok=True)
        output_path = write_research_frame(
            targeted, self._artifact_directory / "v481_neutral_target_panel"
        )
        payload = {
            "version": self.VERSION,
            "stage": "market_neutral_and_sector_neutral_targets",
            "source_path": str(self._source_path),
            "output_path": str(output_path),
            "research_only": True,
            "locked_validation_opened": False,
            "champion_promoted": False,
            **target_summary(targeted),
            "next_step": "Run V4.8.2 cross-sectional ranking models.",
        }
        (self._artifact_directory / "v481_target_summary.json").write_text(
            json.dumps(payload, indent=2, default=str), encoding="utf-8"
        )
        return payload
