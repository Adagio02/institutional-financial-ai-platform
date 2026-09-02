from __future__ import annotations
from pathlib import Path
from typing import Any
import json
from finai.application.services.v453_learning_service import V453LearningService
from finai.domain.learning.v47_universe import load_v47_universe

class V47LearningService(V453LearningService):
    VERSION = "4.7"
    LEARNING_ARCHITECTURE = "multi_asset_universe_foundation"

    def __init__(self, *, v47_universe_path: str = "config/v47_universe.json",
                 v47_artifact_directory: str = "artifacts/v47", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._v47_universe_path = Path(v47_universe_path)
        self._v47_artifact_directory = Path(v47_artifact_directory)
        self._v47_artifact_directory.mkdir(parents=True, exist_ok=True)

    def audit_universe(self, *, interval: str = "1m") -> dict[str, Any]:
        universe = load_v47_universe(self._v47_universe_path)
        rows = []
        for symbol in universe.symbols:
            try:
                bars = self.load_market_bars(symbol=symbol, interval=interval)
                rows.append({
                    "symbol": symbol, "rows": int(len(bars)),
                    "first_bar": None if bars.empty else str(bars["timestamp"].min()),
                    "last_bar": None if bars.empty else str(bars["timestamp"].max()),
                    "ready": bool(len(bars) >= self._minimum_rows),
                })
            except Exception as exc:
                rows.append({"symbol":symbol,"rows":0,"first_bar":None,"last_bar":None,
                             "ready":False,"error":f"{type(exc).__name__}: {exc}"})
        payload = {
            "version":self.VERSION,"interval":interval,"symbol_count":len(universe.symbols),
            "ready_count":sum(bool(x["ready"]) for x in rows),
            "missing_or_insufficient_count":sum(not bool(x["ready"]) for x in rows),
            "instruments":rows,
        }
        path = self._v47_artifact_directory / "v47_universe_audit.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
