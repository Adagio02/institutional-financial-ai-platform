from __future__ import annotations
import json, os
from pathlib import Path
from finai.domain.learning.v48_storage import read_research_frame
from finai.domain.qualification.v55_walk_forward import qualify_walk_forward


class V553QualificationService:
    VERSION = "5.5.3"
    def run(self):
        output = Path(os.getenv("FINAI_V55_ARTIFACT_DIR", "artifacts/v55"))
        metrics = qualify_walk_forward(read_research_frame(output / "v552_oos_portfolio_returns"))
        provenance = os.getenv("FINAI_V55_PROVENANCE", "external_unverified")
        synthetic = provenance.lower() in {"demo", "synthetic", "test"}
        verified_real = provenance.lower() == "real"
        contract = {
            "contract_version": "1.0", "source_stage": self.VERSION,
            "eligible_for_v56_locked_validation": metrics["eligible_for_v56_locked_validation"] and verified_real,
            "eligible_for_untouched_final_test": False, "eligible_for_champion": False,
            "synthetic_data": synthetic, "cloud_execution_compatible": True, "live_trading_enabled": False,
            "required_future_stages": ["5.6", "5.7", "5.8", "5.9"],
            "blocking_reasons": [
                "V5.6-V5.9 gates remain incomplete",
                *(["Synthetic/demo data cannot enter locked validation"] if synthetic else []),
                *(["Data provenance must be explicitly verified as real"] if not verified_real and not synthetic else []),
            ],
        }
        report = {"version": self.VERSION, "stage": "portfolio_level_walk_forward_qualification", "metrics": metrics, "champion_contract": contract, "next_step": "Begin V5.6 only with frozen real data and configuration."}
        (output / "v553_qualification.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        (output / "v553_champion_contract.json").write_text(json.dumps(contract, indent=2), encoding="utf-8")
        (output / "v553_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
