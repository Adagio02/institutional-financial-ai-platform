import os,json
from pathlib import Path
from scripts.cloud_contract_bundle import CONTRACTS,create_bundle,verify_and_extract
def test_signed_bundle_round_trip_and_tamper_detection(tmp_path):
 os.environ["FINAI_CONTRACT_SIGNING_KEY"]="x"*40;root=tmp_path/"contracts"
 for stage,name in CONTRACTS.items():
  p=root/stage;p.mkdir(parents=True);payload={"verified_real_data":True,"synthetic_data":False,"live_trading_enabled":False};(p/name).write_text(json.dumps(payload))
 bundle=tmp_path/"bundle.zip";assert create_bundle(root,bundle)["contracts"]==6;result=verify_and_extract(bundle,tmp_path/"verified");assert result["signature_verified"] and len(list((tmp_path/"verified").rglob("*.json")))==6


def test_s3_client_treats_an_empty_region_as_unset(monkeypatch):
    # GitHub Actions passes AWS_REGION="" when the repository variable is not set.
    import sys
    import types

    from scripts import cloud_contract_bundle

    calls = []
    monkeypatch.setitem(sys.modules, "boto3", types.SimpleNamespace(client=lambda *a, **k: calls.append(k)))
    monkeypatch.delenv("FINAI_S3_ENDPOINT_URL", raising=False)
    monkeypatch.setenv("AWS_REGION", "")
    cloud_contract_bundle.s3_client()
    monkeypatch.setenv("AWS_REGION", "eu-west-1")
    cloud_contract_bundle.s3_client()
    assert [c["region_name"] for c in calls] == ["us-east-1", "eu-west-1"]
