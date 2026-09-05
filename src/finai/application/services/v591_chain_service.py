from __future__ import annotations
import json,os
from pathlib import Path
from finai.domain.champion.v59_eligibility import chain_manifest
class V591ChainService:
 VERSION="5.9.1"
 def run(self):
  out=Path(os.getenv("FINAI_V59_ARTIFACT_DIR","artifacts/v59"));out.mkdir(parents=True,exist_ok=True);root=Path(os.getenv("FINAI_V59_CONTRACT_ROOT","artifacts"));defaults={"v53":"v53/v533_champion_contract.json","v54":"v54/v543_champion_contract.json","v55":"v55/v553_champion_contract.json","v56":"v56/v563_champion_contract.json","v57":"v57/v573_champion_contract.json","v58":"v58/v583_champion_contract.json"};contracts={};paths={}
  for stage,rel in defaults.items():
   p=Path(os.getenv(f"FINAI_V59_{stage.upper()}_CONTRACT",str(root/rel)));paths[stage]=str(p)
   if p.exists():contracts[stage]=json.loads(p.read_text())
  manifest=chain_manifest(contracts);manifest["paths"]=paths;(out/"v591_contract_chain.json").write_text(json.dumps(manifest,indent=2));(out/"v591_contracts_snapshot.json").write_text(json.dumps(contracts,indent=2));report={"version":self.VERSION,"contracts_found":len(contracts),"manifest":manifest};(out/"v591_report.json").write_text(json.dumps(report,indent=2));return report
