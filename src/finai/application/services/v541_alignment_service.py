from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

from finai.domain.ensemble.v54_ensemble import align_signal_families
from finai.domain.learning.v48_storage import read_research_frame, write_research_frame


def _read(path: str) -> pd.DataFrame:
    candidate = Path(path)
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    if path.startswith(("s3://", "gs://", "az://")) or path.lower().endswith(".parquet"):
        return pd.read_parquet(path)
    return read_research_frame(candidate)


class V541AlignmentService:
    VERSION = "5.4.1"

    def run(self):
        output = Path(os.getenv("FINAI_V54_ARTIFACT_DIR", "artifacts/v54"))
        configured = {
            "price": os.getenv("FINAI_V54_PRICE_ALPHA_PATH", "artifacts/v50/v50_alpha_signal_panel"),
            "microstructure": os.getenv("FINAI_V54_MICRO_ALPHA_PATH", "artifacts/v51/v512_microstructure_signals"),
            "options": os.getenv("FINAI_V54_OPTIONS_ALPHA_PATH", "artifacts/v52/v523_options_signals"),
            "fundamental": os.getenv("FINAI_V54_FUNDAMENTAL_ALPHA_PATH", "artifacts/v53/v533_fundamental_event_news_signals"),
        }
        families, skipped = {}, {}
        for name, path in configured.items():
            try:
                families[name] = _read(path)
            except FileNotFoundError:
                skipped[name] = path
        target_path = os.getenv("FINAI_V54_TARGET_PATH", configured["fundamental"])
        target = _read(target_path)
        panel, diagnostics = align_signal_families(families, target)
        output.mkdir(parents=True, exist_ok=True)
        path = write_research_frame(panel, output / "v541_aligned_signal_panel")
        report = {"version": self.VERSION, "panel_path": str(path), "skipped_families": skipped, **diagnostics}
        (output / "v541_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

