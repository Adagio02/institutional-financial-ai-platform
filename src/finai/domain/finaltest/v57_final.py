from __future__ import annotations
import hashlib,json
from typing import Any
import numpy as np,pandas as pd
REQUIRED={"timestamp","symbol","alpha__ensemble","forward_return"}
def normalize(frame:pd.DataFrame)->pd.DataFrame:
 missing=sorted(REQUIRED-set(frame.columns))
 if missing:raise ValueError("V5.7 final input missing: "+", ".join(missing))
 out=frame[sorted(REQUIRED)].copy();out["timestamp"]=pd.to_datetime(out.timestamp,utc=True,errors="coerce");out["symbol"]=out.symbol.astype(str).str.upper().str.strip()
 for c in ("alpha__ensemble","forward_return"):out[c]=pd.to_numeric(out[c],errors="coerce")
 out=out.dropna().drop_duplicates(["timestamp","symbol"]).sort_values(["timestamp","symbol"])
 if out.empty:raise RuntimeError("V5.7 rejected every final-test observation.")
 return out.reset_index(drop=True)
def frame_hash(frame):
 text=normalize(frame).to_csv(index=False,date_format="%Y-%m-%dT%H:%M:%S.%f%z",float_format="%.17g",lineterminator="\n")
 return hashlib.sha256(text.encode()).hexdigest()
def object_hash(value:dict[str,Any])->str:return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def register(frame,config,provenance,upstream_hash):
 p={"schema_version":"1.0","stage":"5.7.1","data_sha256":frame_hash(frame),"config":config,"config_sha256":object_hash(config),"upstream_contract_sha256":upstream_hash,"provenance":provenance,"rows":len(frame),"periods":int(frame.timestamp.nunique()),"symbols":int(frame.symbol.nunique()),"untouched_declared":True,"immutable":True};p["test_id"]=object_hash(p);return p
def execute(frame,long_fraction,cost_bps):
 prior={};rows=[];positions=[]
 for timestamp,s in frame.groupby("timestamp",sort=True,observed=True):
  s=s.copy();pct=s.alpha__ensemble.rank(pct=True,method="first");lo=pct<=long_fraction;hi=pct>=1-long_fraction;s["weight"]=0.
  if hi.any():s.loc[hi,"weight"]=.5/int(hi.sum())
  if lo.any():s.loc[lo,"weight"]=-.5/int(lo.sum())
  current=dict(zip(s.symbol,s.weight));names=set(prior)|set(current);turn=.5*sum(abs(current.get(n,0)-prior.get(n,0)) for n in names);gross=float((s.weight*s.forward_return).sum());cost=turn*cost_bps/10000
  rows.append({"timestamp":timestamp,"gross_return":gross,"turnover":turn,"transaction_cost":cost,"net_return":gross-cost});positions.append(s[["timestamp","symbol","alpha__ensemble","forward_return","weight"]]);prior=current
 return pd.DataFrame(rows),pd.concat(positions,ignore_index=True)
def assess(returns,config):
 net=returns.net_return;eq=(1+net).cumprod();vol=float(net.std(ddof=0));mean=float(net.mean());metrics={"period_count":len(net),"cumulative_net_return":float(eq.iloc[-1]-1),"annualized_sharpe":float(mean/vol*np.sqrt(252)) if vol>0 else 0.,"maximum_drawdown":float((eq/eq.cummax()-1).min()),"positive_period_fraction":float((net>0).mean()),"mean_turnover":float(returns.turnover.mean()),"total_transaction_cost":float(returns.transaction_cost.sum())}
 checks={"minimum_periods":metrics["period_count"]>=config["minimum_periods"],"positive_return":metrics["cumulative_net_return"]>config["minimum_net_return"],"minimum_sharpe":metrics["annualized_sharpe"]>=config["minimum_sharpe"],"drawdown_limit":metrics["maximum_drawdown"]>=-abs(config["maximum_drawdown"]),"turnover_limit":metrics["mean_turnover"]<=config["maximum_mean_turnover"]};return metrics,{"checks":checks,"passed":all(checks.values())}
