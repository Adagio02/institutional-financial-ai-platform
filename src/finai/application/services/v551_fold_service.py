from __future__ import annotations
import json, os
from pathlib import Path
import pandas as pd
from finai.domain.learning.v48_storage import read_research_frame, write_research_frame
from finai.domain.qualification.v55_walk_forward import normalize_ensemble, build_purged_folds, fold_manifest


def _read(path: str) -> pd.DataFrame:
    if path.lower().endswith(".csv"): return pd.read_csv(path)
    if path.startswith(("s3://", "gs://", "az://")) or path.lower().endswith(".parquet"): return pd.read_parquet(path)
    return read_research_frame(Path(path))


class V551FoldService:
    VERSION = "5.5.1"
    def run(self):
        output = Path(os.getenv("FINAI_V55_ARTIFACT_DIR", "artifacts/v55")); output.mkdir(parents=True, exist_ok=True)
        frame = normalize_ensemble(_read(os.getenv("FINAI_V55_ENSEMBLE_PATH", "artifacts/v54/v542_ensemble_signal")))
        folds = build_purged_folds(frame)
        panel_path = write_research_frame(frame, output / "v551_ensemble_panel")
        manifest = fold_manifest(folds, len(frame))
        manifest_path = output / "v551_fold_manifest.json"; manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        report = {"version": self.VERSION, "panel_path": str(panel_path), "manifest_path": str(manifest_path), **manifest}
        (output / "v551_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

