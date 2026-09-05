from __future__ import annotations
import json,os
from pathlib import Path
from finai.domain.champion.v59_eligibility import evaluate
class V592EligibilityService:
 VERSION="5.9.2"
 def run(self):
  out=Path(os.getenv("FINAI_V59_ARTIFACT_DIR","artifacts/v59"));contracts=json.loads((out/"v591_contracts_snapshot.json").read_text());decision=evaluate(contracts);report={"version":self.VERSION,"stage":"champion_eligibility_review","decision":decision};(out/"v592_eligibility_decision.json").write_text(json.dumps(decision,indent=2));(out/"v592_report.json").write_text(json.dumps(report,indent=2));return report
