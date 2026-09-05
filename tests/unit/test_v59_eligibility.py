from finai.domain.champion.v59_eligibility import evaluate,chain_manifest,GATES
def test_v59_fails_closed_and_can_be_eligible():
 assert not evaluate({})["champion_eligible"]
 c={s:{k:True,"live_trading_enabled":False,"verified_real_data":True,"synthetic_data":False} for s,k in GATES.items()};d=evaluate(c);assert d["champion_eligible"] and not d["automatic_promotion"] and d["human_approval_required"];assert chain_manifest(c)["stage_count"]==6
