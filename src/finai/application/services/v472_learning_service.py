from __future__ import annotations
from pathlib import Path
from typing import Any
import json, pandas as pd
from finai.application.services.v471_learning_service import V471LearningService
from finai.domain.learning.v47_universe import load_v47_universe
from finai.domain.learning.v472_relationships import add_relationship_features

class V472LearningService(V471LearningService):
    VERSION = "4.7.2"
    LEARNING_ARCHITECTURE = "market_sector_relationship_layer"

    def __init__(self, *, v472_artifact_directory: str = "artifacts/v472", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._v472_artifact_directory = Path(v472_artifact_directory)
        self._v472_artifact_directory.mkdir(parents=True, exist_ok=True)

    def build_relationship_panel(self) -> dict[str, Any]:
        source = self._v471_artifact_directory/"v471_panel.pkl"
        if not source.exists():
            raise FileNotFoundError("Run V4.7.1 first.")
        panel = pd.read_pickle(source)
        universe = load_v47_universe(self._v47_universe_path)
        enriched = add_relationship_features(panel, universe)
        target = self._v472_artifact_directory/"v472_relationship_panel.pkl"
        enriched.to_pickle(target)
        payload = {
            "version":self.VERSION,"rows":int(len(enriched)),
            "symbols":int(enriched["symbol"].nunique()),
            "sectors":sorted(str(x) for x in enriched["sector"].dropna().unique()),
            "output_path":str(target),
        }
        (self._v472_artifact_directory/"v472_relationship_summary.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        return payload
