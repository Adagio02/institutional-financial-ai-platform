from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finai.domain.learning.v48_storage import read_research_frame
from finai.domain.microstructure.v51_quotes import qualify_microstructure_signals


class V513QualificationService:
    VERSION = "5.1.3"

    def __init__(
        self,
        *,
        signal_path: str = "artifacts/v51/v512_microstructure_signals",
        artifact_directory: str = "artifacts/v51",
    ) -> None:
        self._signal_path = Path(signal_path)
        self._artifact_directory = Path(artifact_directory)

    def run(self) -> dict[str, Any]:
        try:
            signals = read_research_frame(self._signal_path)
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                "V5.1.3 requires the completed V5.1.2 microstructure-signal artifact."
            ) from exc
        qualification = qualify_microstructure_signals(signals)
        if not qualification or not any(item["period_count"] >= 3 for item in qualification):
            raise RuntimeError(
                "V5.1.3 needs at least three synchronized quote periods. "
                "Download minute-bucketed quotes for multiple symbols."
            )
        self._artifact_directory.mkdir(parents=True, exist_ok=True)
        qualification_path = self._artifact_directory / "v513_signal_qualification.json"
        qualification_path.write_text(json.dumps(qualification, indent=2), encoding="utf-8")
        payload = {
            "version": self.VERSION,
            "stage": "forward_return_signal_qualification",
            "signal_count": len(qualification),
            "qualified_signal_count": sum(
                bool(item["eligible_for_v52_research"]) for item in qualification
            ),
            "qualification_path": str(qualification_path),
            "qualification": qualification,
            "research_only": True,
            "live_trading_enabled": False,
            "locked_validation_opened": False,
            "champion_promoted": False,
            "next_step": "Publish V5.1.3 and switch to V5.2.",
        }
        (self._artifact_directory / "v513_report.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        return payload

