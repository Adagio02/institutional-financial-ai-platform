from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finai.domain.learning.v48_storage import read_research_frame, write_research_frame
from finai.domain.options.v52_volatility import build_volatility_surface


class V522SurfaceService:
    VERSION = "5.2.2"

    def __init__(
        self,
        *,
        source_path: str = "artifacts/v52/v521_normalized_option_chain",
        artifact_directory: str = "artifacts/v52",
    ) -> None:
        self._source_path = Path(source_path)
        self._artifact_directory = Path(artifact_directory)

    def run(self) -> dict[str, Any]:
        try:
            chain = read_research_frame(self._source_path)
        except FileNotFoundError as exc:
            raise FileNotFoundError("Run V5.2.1 before V5.2.2.") from exc
        surface = build_volatility_surface(chain)
        if surface.empty:
            raise RuntimeError("V5.2.2 produced no volatility-surface rows.")
        self._artifact_directory.mkdir(parents=True, exist_ok=True)
        output_path = write_research_frame(
            surface, self._artifact_directory / "v522_volatility_surface"
        )
        payload = {
            "version": self.VERSION, "stage": "volatility_surface_features",
            "row_count": int(len(surface)), "symbol_count": int(surface["symbol"].nunique()),
            "timestamp_count": int(surface["timestamp"].nunique()),
            "output_path": str(output_path), "research_only": True,
            "next_step": "Run V5.2.3 options/volatility signal qualification.",
        }
        (self._artifact_directory / "v522_report.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        return payload
