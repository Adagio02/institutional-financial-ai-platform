from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from finai.domain.learning.v483_ic import signal_ic_series, summarize_ic
from finai.domain.learning.v48_storage import read_research_frame, write_research_frame


class V483ICAnalysisService:
    VERSION = "4.8.3"

    def __init__(
        self,
        *,
        source_path: str = "artifacts/v482/v482_oos_predictions",
        artifact_directory: str = "artifacts/v483",
        minimum_cross_section_size: int = 10,
    ) -> None:
        self._source_path = Path(source_path)
        self._artifact_directory = Path(artifact_directory)
        self._minimum_cross_section_size = int(minimum_cross_section_size)

    def run(self) -> dict[str, Any]:
        try:
            frame = read_research_frame(self._source_path)
        except FileNotFoundError as exc:
            raise FileNotFoundError("Run V4.8.2 before V4.8.3.") from exc
        analyses: list[dict[str, Any]] = []
        series_frames: list[pd.DataFrame] = []
        for (target, model_name), candidate in frame.groupby(
            ["target_column", "model_name"], sort=True, observed=True
        ):
            series = signal_ic_series(
                candidate,
                prediction_column="prediction",
                target_column=str(target),
                minimum_cross_section_size=self._minimum_cross_section_size,
            )
            series["target_column"] = str(target)
            series["model_name"] = str(model_name)
            series_frames.append(series)
            analyses.append({
                "target_column": str(target),
                "model_name": str(model_name),
                **summarize_ic(series),
            })
        analyses.sort(
            key=lambda item: (
                item["mean_rank_ic"],
                item["positive_rank_ic_fraction"],
                item["rank_ic_information_ratio"],
            ),
            reverse=True,
        )
        self._artifact_directory.mkdir(parents=True, exist_ok=True)
        series_path = write_research_frame(
            pd.concat(series_frames, ignore_index=True),
            self._artifact_directory / "v483_ic_series",
        )
        payload = {
            "version": self.VERSION,
            "stage": "signal_ic_and_rank_ic_analysis",
            "source_path": str(self._source_path),
            "series_path": str(series_path),
            "candidate_count": len(analyses),
            "leaderboard": analyses,
            "research_leader": analyses[0] if analyses else None,
            "research_only": True,
            "selection_is_not_promotion": True,
            "locked_validation_opened": False,
            "champion_promoted": False,
            "next_step": "Proceed to V4.9 portfolio construction engine research.",
        }
        (self._artifact_directory / "v483_ic_report.json").write_text(
            json.dumps(payload, indent=2, default=str), encoding="utf-8"
        )
        return payload
