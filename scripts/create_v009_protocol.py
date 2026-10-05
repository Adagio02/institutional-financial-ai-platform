import argparse,hashlib,json
from datetime import timedelta
from pathlib import Path
import pandas as pd

p=argparse.ArgumentParser();p.add_argument("--output",required=True);p.add_argument("--contaminated-through",required=True);p.add_argument("--universe",required=True);a=p.parse_args()
out=Path(a.output)
if out.exists():raise FileExistsError(f"Protocol already exists and is immutable: {out}")
cutoff=pd.Timestamp(a.contaminated_through,tz="UTC");locked=cutoff+pd.offsets.BDay(1)
universe=Path(a.universe);digest=hashlib.sha256(universe.read_bytes()).hexdigest()
protocol={
 "protocol_version":"v009.1","created_utc":pd.Timestamp.now(tz="UTC").isoformat(),
 "contaminated_through":cutoff.isoformat(),"prospective_lock_start":locked.isoformat(),
 "universe_path":str(universe),"universe_sha256":digest,"minimum_symbols":80,
 "development":{"training_end":"2022-12-31","calibration":"2023-01-01/2023-12-31","walk_forward":"2024-01-01/contaminated_through"},
 "locked_rules":{"minimum_periods":52,"positive_net_return":True,"minimum_sharpe":.25,"maximum_drawdown":-.30,
  "maximum_mean_turnover":.25,"verified_real_data":True,"single_execution":True},
 "portfolio_policy":"frozen V007: sector/dollar neutral, beta band 0.10, turnover target 0.25, 5-day horizon",
 "live_trading_allowed":False,"v57_allowed_before_locked_pass":False,
}
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(protocol,indent=2),encoding="utf-8")
(out.with_suffix(".sha256")).write_text(hashlib.sha256(out.read_bytes()).hexdigest()+"  "+out.name+"\n",encoding="utf-8")
print(json.dumps(protocol,indent=2))
