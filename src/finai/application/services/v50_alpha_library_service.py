from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finai.domain.alpha.v50_alpha_library import (
    BUILTIN_ALPHAS,
    build_alpha_signal_panel,
    qualify_alpha_library,
)
from finai.domain.learning.v48_storage import read_research_frame, write_research_frame


class V50AlphaLibraryService:
    VERSION = "5.0.3"

    def __init__(
        self,
        *,
        feature_path: str = "artifacts/v481/v481_neutral_target_panel",
        artifact_directory: str = "artifacts/v50",
        target_column: str = "target_market_neutral_return",
    ) -> None:
        self._feature_path = Path(feature_path)
        self._artifact_directory = Path(artifact_directory)
        self._target_column = target_column

    def run(self) -> dict[str, Any]:
        try:
            features = read_research_frame(self._feature_path)
        except FileNotFoundError as exc:
            raise FileNotFoundError("Run V4.8.1 before V5.0.x.") from exc
        signals = build_alpha_signal_panel(features)
        catalog = qualify_alpha_library(
            signals, features, target_column=self._target_column
        )
        self._artifact_directory.mkdir(parents=True, exist_ok=True)
        signal_path = write_research_frame(
            signals, self._artifact_directory / "v50_alpha_signal_panel"
        )
        catalog_path = self._artifact_directory / "v50_alpha_catalog.json"
        catalog_path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
        payload = {
            "version": self.VERSION,
            "stages": {
                "5.0.1": "alpha_definition_registry",
                "5.0.2": "cross_sectional_signal_generation",
                "5.0.3": "alpha_catalog_qualification",
            },
            "alpha_count": len(BUILTIN_ALPHAS),
            "signal_rows": int(len(signals)),
            "signal_columns": [column for column in signals if column.startswith("alpha__")],
            "target_column": self._target_column,
            "signal_path": str(signal_path),
            "catalog_path": str(catalog_path),
            "catalog": catalog,
            "research_only": True,
            "locked_validation_opened": False,
            "champion_promoted": False,
            "next_step": "Run V5.1 quote/microstructure signals.",
        }
        (self._artifact_directory / "v50_report.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        return payload

