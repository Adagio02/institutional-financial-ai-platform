import numpy as np,pandas as pd
from finai.domain.validation.v56_locked import normalize_locked_input,build_lock_manifest,simulate_locked,validation_metrics,decide
def test_v56_lock_is_deterministic_and_cost_aware():
 rng=np.random.default_rng(56);rows=[]
 for d in pd.date_range("2026-01-01",periods=8,tz="UTC"):
  a=rng.normal(size=6)
  for i,x in enumerate(a):rows.append({"timestamp":d,"symbol":str(i),"alpha__ensemble":x,"forward_return":.002*x})
 f=normalize_locked_input(pd.DataFrame(rows));c={"long_fraction":.2,"transaction_cost_bps":5.,"minimum_periods":5,"minimum_net_return":0.,"minimum_sharpe":0.,"maximum_drawdown":.2,"maximum_mean_turnover":1.}
 assert build_lock_manifest(f,c,"demo","x")["lock_id"]==build_lock_manifest(f,c,"demo","x")["lock_id"]
 r,p=simulate_locked(f,.2,5);assert len(r)==8 and len(p)>0 and (r.net_return<=r.gross_return+1e-15).all(); assert decide(validation_metrics(r),c)["passed"]
