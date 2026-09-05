from __future__ import annotations
import json,os
from datetime import datetime,timezone
from pathlib import Path
class V593RegistryService:
 VERSION="5.9.3"
 def run(self):
  out=Path(os.getenv("FINAI_V59_ARTIFACT_DIR","artifacts/v59"));decision=json.loads((out/"v592_eligibility_decision.json").read_text());chain=json.loads((out/"v591_contract_chain.json").read_text());entry={"version":self.VERSION,"candidate_id":chain["chain_sha256"][:20],"evaluated_at":datetime.now(timezone.utc).isoformat(),"status":decision["status"],"champion_eligible":decision["champion_eligible"],"champion_promoted":False,"automatic_promotion":False,"human_approval_required":True,"live_trading_enabled":False,"blocking_reasons":decision["blocking_reasons"]};(out/"v593_candidate_registry.json").write_text(json.dumps(entry,indent=2));report={"version":self.VERSION,"stage":"champion_portfolio_eligibility","candidate":entry,"project_complete_through":"5.9","next_step":"Human governance review only if champion_eligible is true."};(out/"v593_report.json").write_text(json.dumps(report,indent=2));return report
