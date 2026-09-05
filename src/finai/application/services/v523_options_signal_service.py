from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finai.domain.learning.v48_storage import read_research_frame, write_research_frame
from finai.domain.options.v52_volatility import (
    SIGNAL_COLUMNS,
    build_options_signals,
    qualify_options_signals,
)


class V523OptionsSignalService:
    VERSION = "5.2.3"

    def __init__(
        self,
        *,
        source_path: str = "artifacts/v52/v522_volatility_surface",
        artifact_directory: str = "artifacts/v52",
    ) -> None:
        self._source_path = Path(source_path)
        self._artifact_directory = Path(artifact_directory)

    def run(self) -> dict[str, Any]:
        try:
            surface = read_research_frame(self._source_path)
        except FileNotFoundError as exc:
            raise FileNotFoundError("Run V5.2.2 before V5.2.3.") from exc
        signals = build_options_signals(surface)
        qualification = qualify_options_signals(signals)
        if not any(item["period_count"] >= 3 for item in qualification):
            raise RuntimeError("V5.2.3 requires at least three synchronized surface periods.")
        self._artifact_directory.mkdir(parents=True, exist_ok=True)
        signal_path = write_research_frame(
            signals, self._artifact_directory / "v523_options_signals"
        )
        qualification_path = self._artifact_directory / "v523_signal_qualification.json"
        qualification_path.write_text(json.dumps(qualification, indent=2), encoding="utf-8")
        payload = {
            "version": self.VERSION, "stage": "options_volatility_signal_qualification",
            "signal_columns": SIGNAL_COLUMNS, "signal_count": len(SIGNAL_COLUMNS),
            "qualified_signal_count": sum(
                bool(item["eligible_for_v53_research"]) for item in qualification
            ),
            "signal_path": str(signal_path), "qualification_path": str(qualification_path),
            "qualification": qualification, "research_only": True,
            "live_trading_enabled": False, "locked_validation_opened": False,
            "champion_promoted": False,
            "next_step": "Publish V5.2.3 and switch to V5.3.",
        }
        (self._artifact_directory / "v523_report.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        return payload
