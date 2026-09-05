from __future__ import annotations
import json,os
from pathlib import Path
from finai.domain.learning.v48_storage import read_research_frame
from finai.domain.shadow.v58_shadow import metrics,qualify
class V583QualificationService:
 VERSION="5.8.3"
 def run(self):
  out=Path(os.getenv("FINAI_V58_ARTIFACT_DIR","artifacts/v58"));readiness=json.loads((out/"v581_readiness.json").read_text());m=metrics(read_research_frame(out/"v582_shadow_ledger"));q=qualify(m,int(os.getenv("FINAI_V58_MIN_CYCLES","10")),int(os.getenv("FINAI_V58_MIN_DAYS","5")));real=readiness["provenance"].lower()=="real";eligible=q["passed"] and real and readiness["upstream_eligible"]
  c={"contract_version":"1.0","source_stage":self.VERSION,"shadow_qualification_passed":q["passed"],"eligible_for_v59_champion_review":eligible,"eligible_for_champion":False,"verified_real_data":real,"upstream_eligible":readiness["upstream_eligible"],"cloud_execution_compatible":True,"live_trading_enabled":False,"orders_submitted":0,"required_future_stages":["5.9"],"blocking_reasons":["V5.9 champion review remains incomplete",*(["Prospective provenance must be verified real"] if not real else []),*(["V5.7 gate is not eligible"] if not readiness["upstream_eligible"] else []),*(["Shadow thresholds failed"] if not q["passed"] else [])]};report={"version":self.VERSION,"stage":"prospective_autonomous_shadow_qualification","metrics":m,"qualification":q,"champion_contract":c,"next_step":"Begin V5.9 champion review only if eligible."};(out/"v583_qualification.json").write_text(json.dumps(q,indent=2));(out/"v583_champion_contract.json").write_text(json.dumps(c,indent=2));(out/"v583_report.json").write_text(json.dumps(report,indent=2));return report
