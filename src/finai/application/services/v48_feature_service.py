from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from finai.domain.learning.v48_features import (
    V48_FEATURE_COLUMNS,
    build_cross_sectional_feature_platform,
    feature_platform_summary,
)
from finai.domain.learning.v48_storage import write_research_frame


class V48FeatureService:
    VERSION = "4.8"

    def __init__(
        self,
        *,
        source_path: str = "artifacts/v473/v473_cross_sectional_dataset.pkl",
        artifact_directory: str = "artifacts/v48",
        minimum_cross_section_size: int = 10,
        zscore_clip: float = 5.0,
    ) -> None:
        self._source_path = Path(source_path)
        self._artifact_directory = Path(artifact_directory)
        self._minimum_cross_section_size = int(minimum_cross_section_size)
        self._zscore_clip = float(zscore_clip)

    def run(self) -> dict[str, Any]:
        if not self._source_path.exists():
            raise FileNotFoundError("Run V4.7.3 before V4.8.")
        source = pd.read_pickle(self._source_path)
        panel = build_cross_sectional_feature_platform(
            source,
            minimum_cross_section_size=self._minimum_cross_section_size,
            zscore_clip=self._zscore_clip,
        )
        self._artifact_directory.mkdir(parents=True, exist_ok=True)
        panel_path = write_research_frame(
            panel, self._artifact_directory / "v48_feature_panel"
        )
        payload = {
            "version": self.VERSION,
            "stage": "cross_sectional_feature_platform",
            "source_path": str(self._source_path),
            "output_path": str(panel_path),
            "feature_columns": list(V48_FEATURE_COLUMNS),
            "minimum_cross_section_size": self._minimum_cross_section_size,
            "zscore_clip": self._zscore_clip,
            "research_only": True,
            "locked_validation_opened": False,
            "champion_promoted": False,
            **feature_platform_summary(panel),
            "next_step": "Run V4.8.1 market-neutral and sector-neutral targets.",
        }
        (self._artifact_directory / "v48_feature_summary.json").write_text(
            json.dumps(payload, indent=2, default=str), encoding="utf-8"
        )
        return payload
