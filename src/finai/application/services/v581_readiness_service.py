from __future__ import annotations
import json,os
from pathlib import Path
class V581ReadinessService:
 VERSION="5.8.1"
 def run(self):
  out=Path(os.getenv("FINAI_V58_ARTIFACT_DIR","artifacts/v58"));out.mkdir(parents=True,exist_ok=True);up=Path(os.getenv("FINAI_V58_UPSTREAM_CONTRACT","artifacts/v57/v573_champion_contract.json"));contract=json.loads(up.read_text()) if up.exists() else {};ready=bool(contract.get("eligible_for_v58_prospective_shadow",False));provenance=os.getenv("FINAI_V58_PROVENANCE","external_unverified");report={"version":self.VERSION,"upstream_contract":str(up),"upstream_eligible":ready,"provenance":provenance,"mode":"shadow_only","broker_orders_allowed":False,"cloud_execution_compatible":True};(out/"v581_readiness.json").write_text(json.dumps(report,indent=2));return report
