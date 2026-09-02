from __future__ import annotations
from pathlib import Path
from typing import Any
import json
import pandas as pd
from finai.application.services.v47_learning_service import V47LearningService
from finai.domain.learning.v47_universe import load_v47_universe
from finai.domain.learning.v471_panel import build_point_in_time_panel

class V471LearningService(V47LearningService):
    VERSION = "4.7.1"
    LEARNING_ARCHITECTURE = "point_in_time_multi_asset_panel"

    def __init__(self, *, v471_artifact_directory: str = "artifacts/v471", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._v471_artifact_directory = Path(v471_artifact_directory)
        self._v471_artifact_directory.mkdir(parents=True, exist_ok=True)

    def build_panel(self, *, interval: str = "1m", minimum_rows_per_symbol: int = 500) -> dict[str, Any]:
        universe = load_v47_universe(self._v47_universe_path)
        frames: dict[str, pd.DataFrame] = {}
        skipped = []
        for symbol in universe.symbols:
            bars = self.load_market_bars(symbol=symbol, interval=interval)
            if len(bars) < minimum_rows_per_symbol:
                skipped.append({"symbol":symbol,"rows":int(len(bars))})
                continue
            frames[symbol] = bars
        panel = build_point_in_time_panel(frames)
        if panel.empty:
            raise RuntimeError("V4.7.1 cannot build a panel: no symbols have sufficient data.")
        panel_path = self._v471_artifact_directory / "v471_panel.pkl"
        panel.to_pickle(panel_path)
        summary = {
            "version":self.VERSION,"interval":interval,"rows":int(len(panel)),
            "symbols_in_panel":int(panel["symbol"].nunique()),
            "timestamps":int(panel["timestamp"].nunique()),
            "first_timestamp":str(panel["timestamp"].min()),
            "last_timestamp":str(panel["timestamp"].max()),
            "skipped":skipped,"panel_path":str(panel_path),
        }
        (self._v471_artifact_directory/"v471_panel_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        return summary
