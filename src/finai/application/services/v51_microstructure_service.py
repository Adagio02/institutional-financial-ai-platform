from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from finai.domain.learning.v48_storage import read_research_frame, write_research_frame
from finai.domain.microstructure.v51_quotes import (
    SIGNAL_COLUMNS,
    build_microstructure_signals,
    normalize_quotes,
    qualify_microstructure_signals,
)


class V51MicrostructureService:
    VERSION = "5.1.3"

    def __init__(
        self,
        *,
        quote_path: str = "data/research/quotes",
        artifact_directory: str = "artifacts/v51",
    ) -> None:
        self._quote_path = Path(quote_path)
        self._artifact_directory = Path(artifact_directory)

    def _read_quotes(self) -> pd.DataFrame:
        if self._quote_path.suffix.lower() == ".csv":
            if not self._quote_path.exists():
                raise FileNotFoundError(f"V5.1 quote CSV not found: {self._quote_path}")
            return pd.read_csv(self._quote_path)
        try:
            return read_research_frame(self._quote_path)
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                "V5.1 needs historical quotes at data/research/quotes(.parquet/.pkl.gz) "
                "or set FINAI_V51_QUOTE_PATH to a CSV/base path."
            ) from exc

    def run(self) -> dict[str, Any]:
        normalized, quality = normalize_quotes(self._read_quotes())
        signals = build_microstructure_signals(normalized)
        qualification = qualify_microstructure_signals(signals)
        self._artifact_directory.mkdir(parents=True, exist_ok=True)
        normalized_path = write_research_frame(
            normalized, self._artifact_directory / "v511_normalized_quotes"
        )
        signal_path = write_research_frame(
            signals, self._artifact_directory / "v512_microstructure_signals"
        )
        qualification_path = self._artifact_directory / "v513_signal_qualification.json"
        qualification_path.write_text(json.dumps(qualification, indent=2), encoding="utf-8")
        payload = {
            "version": self.VERSION,
            "stages": {
                "5.1.1": "historical_quote_normalization_and_quality",
                "5.1.2": "quote_and_microstructure_signal_generation",
                "5.1.3": "forward_return_signal_qualification",
            },
            "quality": quality,
            "signal_columns": SIGNAL_COLUMNS,
            "signal_count": len(SIGNAL_COLUMNS),
            "normalized_path": str(normalized_path),
            "signal_path": str(signal_path),
            "qualification_path": str(qualification_path),
            "qualification": qualification,
            "research_only": True,
            "live_trading_enabled": False,
            "locked_validation_opened": False,
            "champion_promoted": False,
            "next_step": "Run V5.2 options/volatility signals.",
        }
        (self._artifact_directory / "v51_report.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        return payload

