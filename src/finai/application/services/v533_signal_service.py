from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from finai.domain.fundamental.v53_research import SIGNAL_COLUMNS, build_signals, qualify_signals
from finai.domain.learning.v48_storage import read_research_frame, write_research_frame


class V533SignalService:
    VERSION = "5.3.3"

    def run(self) -> dict[str, Any]:
        output = Path(os.getenv("FINAI_V53_ARTIFACT_DIR", "artifacts/v53"))
        try:
            features = read_research_frame(output / "v532_point_in_time_features")
            manifest = json.loads((output / "v531_dataset_manifest.json").read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise FileNotFoundError("Run V5.3.1 and V5.3.2 before V5.3.3.") from exc
        signals = build_signals(features)
        qualification = qualify_signals(signals)
        path = write_research_frame(signals, output / "v533_fundamental_event_news_signals")
        synthetic = bool(manifest.get("synthetic", True))
        qualified = sum(bool(item["eligible_for_v54_ensemble_research"]) for item in qualification)
        champion_contract = {
            "contract_version": "1.0", "source_stage": self.VERSION,
            "eligible_for_v54_ensemble_research": qualified > 0,
            "eligible_for_locked_validation": False,
            "eligible_for_champion": False,
            "blocking_reasons": [
                "V5.4 ensemble, V5.5 walk-forward, V5.6 locked validation, V5.7 untouched final test, and V5.8 prospective shadow remain incomplete",
                *(["Synthetic/demo data cannot qualify a champion"] if synthetic else []),
            ],
            "required_future_stages": ["5.4", "5.5", "5.6", "5.7", "5.8", "5.9"],
            "cloud_execution_compatible": True,
            "live_trading_enabled": False,
        }
        report = {
            "version": self.VERSION, "stage": "fundamental_event_news_signal_qualification",
            "signal_path": str(path), "signal_columns": SIGNAL_COLUMNS,
            "qualified_signal_count": qualified, "qualification": qualification,
            "synthetic_data": synthetic, "champion_contract": champion_contract,
            "next_step": "Publish V5.3.3 and begin V5.4 alpha ensemble.",
        }
        output.mkdir(parents=True, exist_ok=True)
        (output / "v533_signal_qualification.json").write_text(json.dumps(qualification, indent=2), encoding="utf-8")
        (output / "v533_champion_contract.json").write_text(json.dumps(champion_contract, indent=2), encoding="utf-8")
        (output / "v533_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

