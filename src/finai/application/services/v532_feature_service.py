from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from finai.domain.fundamental.v53_research import build_point_in_time_features
from finai.domain.learning.v48_storage import read_research_frame, write_research_frame


class V532FeatureService:
    VERSION = "5.3.2"

    def run(self) -> dict[str, Any]:
        output = Path(os.getenv("FINAI_V53_ARTIFACT_DIR", "artifacts/v53"))
        try:
            frames = {name: read_research_frame(output / f"v531_{name}") for name in ("fundamentals", "events", "news", "prices")}
        except FileNotFoundError as exc:
            raise FileNotFoundError("Run V5.3.1 before V5.3.2.") from exc
        features = build_point_in_time_features(**frames)
        path = write_research_frame(features, output / "v532_point_in_time_features")
        report = {
            "version": self.VERSION, "feature_path": str(path), "rows": int(len(features)),
            "symbols": int(features["symbol"].nunique()), "periods": int(features["timestamp"].nunique()),
            "lookahead_violations": int((features["source_available_at"] > features["timestamp"]).sum()),
        }
        (output / "v532_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

