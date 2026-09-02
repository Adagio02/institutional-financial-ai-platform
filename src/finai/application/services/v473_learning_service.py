from __future__ import annotations
from pathlib import Path
from typing import Any
import json, pandas as pd
from finai.application.services.v472_learning_service import V472LearningService
from finai.domain.learning.v473_cross_sectional import V473_FEATURE_COLUMNS, add_cross_sectional_targets

class V473LearningService(V472LearningService):
    VERSION = "4.7.3"
    LEARNING_ARCHITECTURE = "cross_sectional_feature_and_target_foundation"

    def __init__(self, *, v473_artifact_directory: str = "artifacts/v473", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._v473_artifact_directory = Path(v473_artifact_directory)
        self._v473_artifact_directory.mkdir(parents=True, exist_ok=True)

    def build_cross_sectional_dataset(self, *, horizon_bars: int = 30) -> dict[str, Any]:
        source = self._v472_artifact_directory/"v472_relationship_panel.pkl"
        if not source.exists():
            raise FileNotFoundError("Run V4.7.2 first.")
        panel = pd.read_pickle(source)
        dataset = add_cross_sectional_targets(panel, horizon_bars=horizon_bars)
        equity = dataset.loc[dataset["sector"] != "ETF"].copy()
        required = V473_FEATURE_COLUMNS + [
            "future_market_excess_return","future_benchmark_excess_return","target_cross_sectional_rank"
        ]
        usable = equity.dropna(subset=required).copy()
        target = self._v473_artifact_directory/"v473_cross_sectional_dataset.pkl"
        usable.to_pickle(target)
        coverage = (
            usable.groupby("symbol").size().sort_values(ascending=False).astype(int).to_dict()
        )
        payload = {
            "version":self.VERSION,"horizon_bars":int(horizon_bars),
            "rows":int(len(usable)),"symbols":int(usable["symbol"].nunique()),
            "timestamps":int(usable["timestamp"].nunique()),
            "feature_columns":V473_FEATURE_COLUMNS,
            "target_columns":["future_market_excess_return","future_benchmark_excess_return",
                              "target_cross_sectional_rank"],
            "rows_per_symbol":coverage,"output_path":str(target),
            "research_only":True,"promotion_attempted":False,
        }
        (self._v473_artifact_directory/"v473_dataset_summary.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        return payload
