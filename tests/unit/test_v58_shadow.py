import numpy as np,pandas as pd
from finai.domain.shadow.v58_shadow import normalize,replay,metrics,qualify
def test_v58_no_order_cost_aware_shadow():
 rng=np.random.default_rng(58);rows=[];prices=np.ones(6)*100
 for d in pd.date_range("2026-01-01",periods=10,tz="UTC"):
  a=rng.normal(size=6);prices*=1+.003*a
  for i,x,p in zip(range(6),a,prices):rows.append({"timestamp":d,"symbol":str(i),"alpha__ensemble":x,"price":p})
 f=normalize(pd.DataFrame(rows));l,p=replay(f);assert not p.order_submitted.any() and (l.net_return<=l.gross_return+1e-15).all();m=metrics(l);q=qualify(m,10,5);assert m["orders_submitted"]==0 and q["checks"]["minimum_cycles"] and q["checks"]["no_orders"]
