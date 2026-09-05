from __future__ import annotations
from typing import Any
import numpy as np,pandas as pd
REQUIRED={"timestamp","symbol","alpha__ensemble","price"}
def normalize(frame):
 missing=sorted(REQUIRED-set(frame.columns))
 if missing:raise ValueError("V5.8 snapshot input missing: "+", ".join(missing))
 out=frame[sorted(REQUIRED)].copy();out["timestamp"]=pd.to_datetime(out.timestamp,utc=True,errors="coerce");out["symbol"]=out.symbol.astype(str).str.upper().str.strip()
 for c in ("alpha__ensemble","price"):out[c]=pd.to_numeric(out[c],errors="coerce")
 out=out.dropna().loc[lambda x:x.price>0].drop_duplicates(["timestamp","symbol"],keep="last").sort_values(["timestamp","symbol"])
 if out.empty:raise RuntimeError("V5.8 rejected every snapshot.")
 return out.reset_index(drop=True)
def replay(frame,long_fraction=.2,cost_bps=5.):
 previous_prices={};previous_weights={};ledger=[];positions=[]
 for timestamp,s in normalize(frame).groupby("timestamp",sort=True,observed=True):
  s=s.copy();current_prices=dict(zip(s.symbol,s.price));realized=sum(previous_weights.get(n,0)*(current_prices[n]/previous_prices[n]-1) for n in set(current_prices)&set(previous_prices)&set(previous_weights))
  pct=s.alpha__ensemble.rank(pct=True,method="first");lo=pct<=long_fraction;hi=pct>=1-long_fraction;s["weight"]=0.
  if hi.any():s.loc[hi,"weight"]=.5/int(hi.sum())
  if lo.any():s.loc[lo,"weight"]=-.5/int(lo.sum())
  current_weights=dict(zip(s.symbol,s.weight));names=set(previous_weights)|set(current_weights);turn=.5*sum(abs(current_weights.get(n,0)-previous_weights.get(n,0)) for n in names);cost=turn*cost_bps/10000
  ledger.append({"timestamp":timestamp,"gross_return":float(realized),"turnover":turn,"transaction_cost":cost,"net_return":float(realized-cost),"gross_exposure":float(s.weight.abs().sum()),"net_exposure":float(s.weight.sum()),"symbol_count":len(s)})
  s["decision_timestamp"]=timestamp;s["order_submitted"]=False;positions.append(s[["decision_timestamp","symbol","price","alpha__ensemble","weight","order_submitted"]]);previous_prices=current_prices;previous_weights=current_weights
 return pd.DataFrame(ledger),pd.concat(positions,ignore_index=True)
def metrics(ledger):
 net=ledger.net_return;eq=(1+net).cumprod();vol=float(net.std(ddof=0));mean=float(net.mean());return {"cycle_count":len(net),"elapsed_calendar_days":int((ledger.timestamp.max()-ledger.timestamp.min()).days),"cumulative_net_return":float(eq.iloc[-1]-1),"annualized_sharpe":float(mean/vol*np.sqrt(252)) if vol>0 else 0.,"maximum_drawdown":float((eq/eq.cummax()-1).min()),"positive_cycle_fraction":float((net>0).mean()),"mean_turnover":float(ledger.turnover.mean()),"total_transaction_cost":float(ledger.transaction_cost.sum()),"orders_submitted":0}
def qualify(m:dict[str,Any],minimum_cycles:int,minimum_days:int):
 checks={"minimum_cycles":bool(m["cycle_count"]>=minimum_cycles),"minimum_elapsed_days":bool(m["elapsed_calendar_days"]>=minimum_days),"positive_net_return":bool(m["cumulative_net_return"]>0),"finite_sharpe":bool(np.isfinite(m["annualized_sharpe"])),"no_orders":bool(m["orders_submitted"]==0)};return {"checks":checks,"passed":bool(all(checks.values()))}
