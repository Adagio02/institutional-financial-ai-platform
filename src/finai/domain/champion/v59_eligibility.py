from __future__ import annotations
import hashlib,json
from typing import Any
GATES={"v53":"eligible_for_v54_ensemble_research","v54":"eligible_for_v55_walk_forward","v55":"eligible_for_v56_locked_validation","v56":"eligible_for_v57_untouched_final_test","v57":"eligible_for_v58_prospective_shadow","v58":"eligible_for_v59_champion_review"}
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
def evaluate(contracts:dict[str,dict[str,Any]])->dict[str,Any]:
 checks={};reasons=[]
 for stage,key in GATES.items():
  present=stage in contracts;passed=bool(contracts.get(stage,{}).get(key,False));checks[f"{stage}_present"]=present;checks[f"{stage}_gate"]=passed
  if not present:reasons.append(f"Missing {stage} contract")
  elif not passed:reasons.append(f"{stage} gate {key} is false")
 for stage in ("v55","v56","v57","v58"):
  c=contracts.get(stage,{});real=bool(c.get("verified_real_data",False)) if stage!="v55" else not bool(c.get("synthetic_data",True))
  checks[f"{stage}_real_data"]=real
  if not real:reasons.append(f"{stage} does not attest verified real data")
 no_live=all(not bool(c.get("live_trading_enabled",False)) for c in contracts.values());checks["no_live_trading_during_research"]=no_live
 if not no_live:reasons.append("A research contract enabled live trading")
 eligible=all(checks.values())
 return {"checks":checks,"champion_eligible":eligible,"status":"eligible" if eligible else "ineligible","blocking_reasons":reasons,"automatic_promotion":False,"human_approval_required":True}
def chain_manifest(contracts):
 hashes={k:digest(v) for k,v in sorted(contracts.items())};p={"schema_version":"1.0","contract_hashes":hashes,"stage_count":len(hashes)};p["chain_sha256"]=digest(p);return p
