import numpy as np,pandas as pd
from finai.domain.finaltest.v57_final import normalize,register,execute,assess
def test_v57_is_deterministic_cost_aware_and_passes_good_panel():
 rng=np.random.default_rng(57);rows=[]
 for d in pd.date_range("2026-01-01",periods=8,tz="UTC"):
  a=rng.normal(size=6)
  for i,x in enumerate(a):rows.append({"timestamp":d,"symbol":str(i),"alpha__ensemble":x,"forward_return":.003*x})
 f=normalize(pd.DataFrame(rows));c={"long_fraction":.2,"transaction_cost_bps":5.,"minimum_periods":5,"minimum_net_return":0.,"minimum_sharpe":0.,"maximum_drawdown":.2,"maximum_mean_turnover":1.};assert register(f,c,"demo","x")["test_id"]==register(f,c,"demo","x")["test_id"];r,p=execute(f,.2,5);m,d=assess(r,c);assert len(p)>0 and d["passed"] and (r.net_return<=r.gross_return+1e-15).all()
