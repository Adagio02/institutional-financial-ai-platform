from __future__ import annotations
import hashlib,json,os
from pathlib import Path
import pandas as pd
from finai.domain.learning.v48_storage import read_research_frame,write_research_frame
from finai.domain.validation.v56_locked import normalize_locked_input,build_lock_manifest

def _read(path:str):
    if path.lower().endswith(".csv"): return pd.read_csv(path)
    if path.startswith(("s3://","gs://","az://")) or path.lower().endswith(".parquet"): return pd.read_parquet(path)
    return read_research_frame(Path(path))

class V561LockService:
    VERSION="5.6.1"
    def run(self):
        out=Path(os.getenv("FINAI_V56_ARTIFACT_DIR","artifacts/v56")); out.mkdir(parents=True,exist_ok=True)
        frame=normalize_locked_input(_read(os.getenv("FINAI_V56_INPUT_PATH","data/research/v56/locked_input.csv")))
        config={"long_fraction":float(os.getenv("FINAI_V56_LONG_FRACTION","0.20")),"transaction_cost_bps":float(os.getenv("FINAI_V56_COST_BPS","5")),"minimum_periods":int(os.getenv("FINAI_V56_MIN_PERIODS","5")),"minimum_net_return":float(os.getenv("FINAI_V56_MIN_RETURN","0")),"minimum_sharpe":float(os.getenv("FINAI_V56_MIN_SHARPE","0")),"maximum_drawdown":float(os.getenv("FINAI_V56_MAX_DRAWDOWN","0.20")),"maximum_mean_turnover":float(os.getenv("FINAI_V56_MAX_TURNOVER","1.0"))}
        upstream=Path("artifacts/v55/v553_champion_contract.json")
        upstream_hash=hashlib.sha256(upstream.read_bytes()).hexdigest() if upstream.exists() else "unavailable"
        manifest=build_lock_manifest(frame,config,os.getenv("FINAI_V56_PROVENANCE","external_unverified"),upstream_hash)
        manifest_path=out/"v561_lock_manifest.json"
        if manifest_path.exists():
            existing=json.loads(manifest_path.read_text(encoding="utf-8"))
            if existing.get("lock_id")!=manifest["lock_id"]: raise RuntimeError("V5.6 lock already exists with different data or configuration.")
        else: manifest_path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
        data_path=write_research_frame(frame,out/"v561_locked_input")
        report={"version":self.VERSION,"lock_id":manifest["lock_id"],"manifest_path":str(manifest_path),"locked_input_path":str(data_path),"immutable":True}
        (out/"v561_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8"); return report

