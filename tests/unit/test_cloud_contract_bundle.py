import os,json
from pathlib import Path
from scripts.cloud_contract_bundle import CONTRACTS,create_bundle,verify_and_extract
def test_signed_bundle_round_trip_and_tamper_detection(tmp_path):
 os.environ["FINAI_CONTRACT_SIGNING_KEY"]="x"*40;root=tmp_path/"contracts"
 for stage,name in CONTRACTS.items():
  p=root/stage;p.mkdir(parents=True);payload={"verified_real_data":True,"synthetic_data":False,"live_trading_enabled":False};(p/name).write_text(json.dumps(payload))
 bundle=tmp_path/"bundle.zip";assert create_bundle(root,bundle)["contracts"]==6;result=verify_and_extract(bundle,tmp_path/"verified");assert result["signature_verified"] and len(list((tmp_path/"verified").rglob("*.json")))==6
