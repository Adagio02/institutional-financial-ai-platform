from __future__ import annotations
import json,os
from pathlib import Path
from finai.domain.finaltest.v57_final import frame_hash,execute,assess
from finai.domain.learning.v48_storage import read_research_frame,write_research_frame
class V572ExecutionService:
 VERSION="5.7.2"
 def run(self):
  out=Path(os.getenv("FINAI_V57_ARTIFACT_DIR","artifacts/v57"));m=json.loads((out/"v571_final_test_manifest.json").read_text());f=read_research_frame(out/"v571_final_input")
  if frame_hash(f)!=m["data_sha256"]:raise RuntimeError("V5.7 final input hash mismatch.")
  rp=out/"v572_execution_receipt.json"
  if rp.exists():
   r=json.loads(rp.read_text());
   if r.get("test_id")!=m["test_id"]:raise RuntimeError("V5.7 receipt belongs to another test.")
   return r
  ret,pos=execute(f,m["config"]["long_fraction"],m["config"]["transaction_cost_bps"]);metrics,decision=assess(ret,m["config"]);retp=write_research_frame(ret,out/"v572_final_returns");posp=write_research_frame(pos,out/"v572_final_positions");r={"version":self.VERSION,"test_id":m["test_id"],"execution_count":1,"returns_path":str(retp),"positions_path":str(posp),"metrics":metrics,"decision":decision,"completed":True};rp.write_text(json.dumps(r,indent=2));return r
