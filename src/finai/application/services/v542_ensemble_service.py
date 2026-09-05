from __future__ import annotations

import json
import os
from pathlib import Path

from finai.domain.ensemble.v54_ensemble import build_expanding_ensemble
from finai.domain.learning.v48_storage import read_research_frame, write_research_frame


class V542EnsembleService:
    VERSION = "5.4.2"

    def run(self):
        output = Path(os.getenv("FINAI_V54_ARTIFACT_DIR", "artifacts/v54"))
        panel = read_research_frame(output / "v541_aligned_signal_panel")
        ensemble, weights = build_expanding_ensemble(panel)
        ensemble_path = write_research_frame(ensemble, output / "v542_ensemble_signal")
        weights_path = write_research_frame(weights, output / "v542_expanding_weights")
        report = {
            "version": self.VERSION, "ensemble_path": str(ensemble_path), "weights_path": str(weights_path),
            "rows": int(len(ensemble)), "periods": int(ensemble["timestamp"].nunique()),
            "lookahead_policy": "weights_at_t_use_only_targets_available_before_t",
        }
        (output / "v542_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

