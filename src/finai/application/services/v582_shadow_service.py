from __future__ import annotations
import json,os
from pathlib import Path
import pandas as pd
from finai.domain.learning.v48_storage import read_research_frame,write_research_frame
from finai.domain.shadow.v58_shadow import normalize,replay
def _read(p):
 if p.lower().endswith(".csv"):return pd.read_csv(p)
 if p.startswith(("s3://","gs://","az://")) or p.lower().endswith(".parquet"):return pd.read_parquet(p)
 return read_research_frame(Path(p))
class V582ShadowService:
 VERSION="5.8.2"
 def run(self):
  out=Path(os.getenv("FINAI_V58_ARTIFACT_DIR","artifacts/v58"));frame=normalize(_read(os.getenv("FINAI_V58_SNAPSHOT_PATH","data/research/v58/snapshots.csv")));ledger,positions=replay(frame,float(os.getenv("FINAI_V58_LONG_FRACTION",".2")),float(os.getenv("FINAI_V58_COST_BPS","5")));lp=write_research_frame(ledger,out/"v582_shadow_ledger");pp=write_research_frame(positions,out/"v582_shadow_positions");report={"version":self.VERSION,"ledger_path":str(lp),"positions_path":str(pp),"cycles":len(ledger),"orders_submitted":0,"mode":"shadow_only"};(out/"v582_report.json").write_text(json.dumps(report,indent=2));return report
