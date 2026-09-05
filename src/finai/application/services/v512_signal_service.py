from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finai.domain.learning.v48_storage import read_research_frame, write_research_frame
from finai.domain.microstructure.v51_quotes import SIGNAL_COLUMNS, build_microstructure_signals


class V512SignalService:
    VERSION = "5.1.2"

    def __init__(
        self,
        *,
        normalized_path: str = "artifacts/v51/v511_normalized_quotes",
        artifact_directory: str = "artifacts/v51",
    ) -> None:
        self._normalized_path = Path(normalized_path)
        self._artifact_directory = Path(artifact_directory)

    def run(self) -> dict[str, Any]:
        try:
            normalized = read_research_frame(self._normalized_path)
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                "V5.1.2 requires the completed V5.1.1 normalized-quotes artifact."
            ) from exc
        signals = build_microstructure_signals(normalized)
        self._artifact_directory.mkdir(parents=True, exist_ok=True)
        signal_path = write_research_frame(
            signals, self._artifact_directory / "v512_microstructure_signals"
        )
        payload = {
            "version": self.VERSION,
            "stage": "quote_and_microstructure_signal_generation",
            "input_rows": int(len(normalized)),
            "output_rows": int(len(signals)),
            "timestamp_count": int(signals["timestamp"].nunique()),
            "symbol_count": int(signals["symbol"].nunique()),
            "signal_columns": SIGNAL_COLUMNS,
            "signal_path": str(signal_path),
            "research_only": True,
            "next_step": "Run V5.1.3 signal qualification.",
        }
        (self._artifact_directory / "v512_report.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        return payload

