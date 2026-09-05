from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

from finai.domain.fundamental.v53_research import (
    dataset_manifest, normalize_events, normalize_fundamentals, normalize_news, normalize_prices,
)
from finai.domain.learning.v48_storage import write_research_frame


def _read(path: str) -> pd.DataFrame:
    lower = path.lower()
    if lower.endswith(".csv"):
        return pd.read_csv(path)
    if lower.endswith(".parquet") or path.startswith(("s3://", "gs://", "az://")):
        return pd.read_parquet(path)
    candidate = Path(path)
    if candidate.with_suffix(".parquet").exists():
        return pd.read_parquet(candidate.with_suffix(".parquet"))
    if candidate.with_suffix(".pkl.gz").exists():
        return pd.read_pickle(candidate.with_suffix(".pkl.gz"))
    raise FileNotFoundError(f"V5.3 data source not found: {path}")


class V531DataService:
    VERSION = "5.3.1"

    def run(self) -> dict[str, Any]:
        output = Path(os.getenv("FINAI_V53_ARTIFACT_DIR", "artifacts/v53"))
        sources = {
            "fundamentals": os.getenv("FINAI_V53_FUNDAMENTAL_PATH", "data/research/v53/fundamentals.csv"),
            "events": os.getenv("FINAI_V53_EVENT_PATH", "data/research/v53/events.csv"),
            "news": os.getenv("FINAI_V53_NEWS_PATH", "data/research/v53/news.csv"),
            "prices": os.getenv("FINAI_V53_PRICE_PATH", "data/research/v53/prices.csv"),
        }
        frames = {
            "fundamentals": normalize_fundamentals(_read(sources["fundamentals"])),
            "events": normalize_events(_read(sources["events"])),
            "news": normalize_news(_read(sources["news"])),
            "prices": normalize_prices(_read(sources["prices"])),
        }
        output.mkdir(parents=True, exist_ok=True)
        paths = {name: str(write_research_frame(frame, output / f"v531_{name}")) for name, frame in frames.items()}
        provenance = os.getenv("FINAI_V53_PROVENANCE", "external_unverified")
        manifest = dataset_manifest(frames, provenance)
        manifest_path = output / "v531_dataset_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        report = {"version": self.VERSION, "paths": paths, "manifest_path": str(manifest_path), **manifest}
        (output / "v531_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

