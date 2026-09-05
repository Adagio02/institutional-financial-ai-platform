from __future__ import annotations
import json,os
from pathlib import Path
from finai.domain.learning.v48_storage import read_research_frame,write_research_frame
from finai.domain.validation.v56_locked import canonical_frame_hash,simulate_locked,validation_metrics

class V562ExecutionService:
    VERSION="5.6.2"
    def run(self):
        out=Path(os.getenv("FINAI_V56_ARTIFACT_DIR","artifacts/v56")); manifest=json.loads((out/"v561_lock_manifest.json").read_text())
        frame=read_research_frame(out/"v561_locked_input")
        if canonical_frame_hash(frame)!=manifest["data_sha256"]: raise RuntimeError("V5.6 locked input hash mismatch.")
        marker=out/"v562_execution_receipt.json"
        if marker.exists():
            receipt=json.loads(marker.read_text());
            if receipt.get("lock_id")!=manifest["lock_id"]: raise RuntimeError("V5.6 execution receipt belongs to another lock.")
            return receipt
        config=manifest["config"]; returns,positions=simulate_locked(frame,config["long_fraction"],config["transaction_cost_bps"]); metrics=validation_metrics(returns)
        returns_path=write_research_frame(returns,out/"v562_locked_returns"); positions_path=write_research_frame(positions,out/"v562_locked_positions")
        receipt={"version":self.VERSION,"lock_id":manifest["lock_id"],"execution_count":1,"returns_path":str(returns_path),"positions_path":str(positions_path),"metrics":metrics,"completed":True}
        marker.write_text(json.dumps(receipt,indent=2),encoding="utf-8"); return receipt

