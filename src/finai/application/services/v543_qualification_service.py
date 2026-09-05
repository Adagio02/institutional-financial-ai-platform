from __future__ import annotations

import json
import os
from pathlib import Path

from finai.domain.ensemble.v54_ensemble import qualify_ensemble
from finai.domain.learning.v48_storage import read_research_frame


class V543QualificationService:
    VERSION = "5.4.3"

    def run(self):
        output = Path(os.getenv("FINAI_V54_ARTIFACT_DIR", "artifacts/v54"))
        ensemble = read_research_frame(output / "v542_ensemble_signal")
        weights = read_research_frame(output / "v542_expanding_weights")
        qualification = qualify_ensemble(ensemble, weights)
        provenance = os.getenv("FINAI_V54_PROVENANCE", "external_unverified")
        synthetic = provenance.lower() in {"demo", "synthetic", "test"}
        contract = {
            "contract_version": "1.0", "source_stage": self.VERSION,
            "eligible_for_v55_walk_forward": qualification["eligible_for_v55_walk_forward"],
            "eligible_for_locked_validation": False, "eligible_for_champion": False,
            "synthetic_data": synthetic, "cloud_execution_compatible": True,
            "live_trading_enabled": False,
            "required_future_stages": ["5.5", "5.6", "5.7", "5.8", "5.9"],
            "blocking_reasons": [
                "V5.5-V5.9 qualification gates remain incomplete",
                *(["Synthetic/demo data cannot qualify a champion"] if synthetic else []),
            ],
        }
        report = {
            "version": self.VERSION, "stage": "multi_strategy_alpha_ensemble_qualification",
            "qualification": qualification, "champion_contract": contract,
            "next_step": "Publish V5.4.3 and begin V5.5 portfolio walk-forward qualification.",
        }
        output.mkdir(parents=True, exist_ok=True)
        (output / "v543_qualification.json").write_text(json.dumps(qualification, indent=2), encoding="utf-8")
        (output / "v543_champion_contract.json").write_text(json.dumps(contract, indent=2), encoding="utf-8")
        (output / "v543_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

