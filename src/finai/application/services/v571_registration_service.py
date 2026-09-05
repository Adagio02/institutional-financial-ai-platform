from __future__ import annotations
import hashlib,json,os
from pathlib import Path
import pandas as pd
from finai.domain.finaltest.v57_final import normalize,register
from finai.domain.learning.v48_storage import read_research_frame,write_research_frame
def _read(p):
 if p.lower().endswith(".csv"):return pd.read_csv(p)
 if p.startswith(("s3://","gs://","az://")) or p.lower().endswith(".parquet"):return pd.read_parquet(p)
 return read_research_frame(Path(p))
class V571RegistrationService:
 VERSION="5.7.1"
 def run(self):
  out=Path(os.getenv("FINAI_V57_ARTIFACT_DIR","artifacts/v57"));out.mkdir(parents=True,exist_ok=True);frame=normalize(_read(os.getenv("FINAI_V57_INPUT_PATH","data/research/v57/final_input.csv")))
  config={"long_fraction":float(os.getenv("FINAI_V57_LONG_FRACTION",".20")),"transaction_cost_bps":float(os.getenv("FINAI_V57_COST_BPS","5")),"minimum_periods":int(os.getenv("FINAI_V57_MIN_PERIODS","5")),"minimum_net_return":float(os.getenv("FINAI_V57_MIN_RETURN","0")),"minimum_sharpe":float(os.getenv("FINAI_V57_MIN_SHARPE","0")),"maximum_drawdown":float(os.getenv("FINAI_V57_MAX_DRAWDOWN",".20")),"maximum_mean_turnover":float(os.getenv("FINAI_V57_MAX_TURNOVER","1"))}
  upstream=Path(os.getenv("FINAI_V57_UPSTREAM_CONTRACT","artifacts/v56/v563_champion_contract.json"));uh=hashlib.sha256(upstream.read_bytes()).hexdigest() if upstream.exists() else "unavailable";manifest=register(frame,config,os.getenv("FINAI_V57_PROVENANCE","external_unverified"),uh);mp=out/"v571_final_test_manifest.json"
  if mp.exists() and json.loads(mp.read_text()).get("test_id")!=manifest["test_id"]:raise RuntimeError("V5.7 final test already registered with different data or configuration.")
  if not mp.exists():mp.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
  dp=write_research_frame(frame,out/"v571_final_input");report={"version":self.VERSION,"test_id":manifest["test_id"],"manifest_path":str(mp),"input_path":str(dp),"immutable":True};(out/"v571_report.json").write_text(json.dumps(report,indent=2));return report
