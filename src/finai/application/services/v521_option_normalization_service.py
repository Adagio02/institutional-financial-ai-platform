from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from finai.domain.learning.v48_storage import read_research_frame, write_research_frame
from finai.domain.options.v52_volatility import normalize_option_chain


class V521OptionNormalizationService:
    VERSION = "5.2.1"

    def __init__(
        self,
        *,
        source_path: str = "data/research/options_chain",
        artifact_directory: str = "artifacts/v52",
    ) -> None:
        self._source_path = Path(source_path)
        self._artifact_directory = Path(artifact_directory)

    def _read(self) -> pd.DataFrame:
        if self._source_path.suffix.lower() == ".csv":
            if not self._source_path.exists():
                raise FileNotFoundError(f"V5.2 options CSV not found: {self._source_path}")
            return pd.read_csv(self._source_path)
        try:
            return read_research_frame(self._source_path)
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                "V5.2.1 requires an options-chain CSV or research frame."
            ) from exc

    def run(self) -> dict[str, Any]:
        normalized, quality = normalize_option_chain(self._read())
        self._artifact_directory.mkdir(parents=True, exist_ok=True)
        output_path = write_research_frame(
            normalized, self._artifact_directory / "v521_normalized_option_chain"
        )
        payload = {
            "version": self.VERSION, "stage": "option_chain_normalization",
            "quality": quality, "symbol_count": int(normalized["underlying_symbol"].nunique()),
            "timestamp_count": int(normalized["timestamp"].nunique()),
            "output_path": str(output_path), "research_only": True,
            "next_step": "Run V5.2.2 volatility-surface features.",
        }
        (self._artifact_directory / "v521_report.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        return payload
