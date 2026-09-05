from __future__ import annotations
import json,os
from pathlib import Path
from finai.domain.validation.v56_locked import decide

class V563DecisionService:
    VERSION="5.6.3"
    def run(self):
        out=Path(os.getenv("FINAI_V56_ARTIFACT_DIR","artifacts/v56")); manifest=json.loads((out/"v561_lock_manifest.json").read_text()); receipt=json.loads((out/"v562_execution_receipt.json").read_text())
        if receipt["lock_id"]!=manifest["lock_id"]: raise RuntimeError("V5.6 lock/receipt mismatch.")
        decision=decide(receipt["metrics"],manifest["config"]); verified_real=manifest["provenance"].lower()=="real"
        contract={"contract_version":"1.0","source_stage":self.VERSION,"lock_id":manifest["lock_id"],"validation_passed":decision["passed"],"eligible_for_v57_untouched_final_test":decision["passed"] and verified_real,"eligible_for_champion":False,"verified_real_data":verified_real,"cloud_execution_compatible":True,"live_trading_enabled":False,"required_future_stages":["5.7","5.8","5.9"],"blocking_reasons":["V5.7-V5.9 remain incomplete",*(["Locked data provenance must be explicitly verified as real"] if not verified_real else []),*(["Locked validation thresholds failed"] if not decision["passed"] else [])]}
        report={"version":self.VERSION,"stage":"locked_validation_decision","metrics":receipt["metrics"],"decision":decision,"champion_contract":contract,"next_step":"Run V5.7 untouched final test only if eligible."}
        (out/"v563_decision.json").write_text(json.dumps(decision,indent=2),encoding="utf-8"); (out/"v563_champion_contract.json").write_text(json.dumps(contract,indent=2),encoding="utf-8"); (out/"v563_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8"); return report
