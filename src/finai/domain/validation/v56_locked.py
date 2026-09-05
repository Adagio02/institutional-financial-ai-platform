from __future__ import annotations
import hashlib, json
from typing import Any
import numpy as np
import pandas as pd

REQUIRED={"timestamp","symbol","alpha__ensemble","forward_return"}

def normalize_locked_input(frame: pd.DataFrame) -> pd.DataFrame:
    missing=sorted(REQUIRED-set(frame.columns))
    if missing: raise ValueError("V5.6 locked input missing: "+", ".join(missing))
    out=frame[sorted(REQUIRED)].copy()
    out["timestamp"]=pd.to_datetime(out["timestamp"],utc=True,errors="coerce")
    out["symbol"]=out["symbol"].astype(str).str.upper().str.strip()
    for c in ("alpha__ensemble","forward_return"): out[c]=pd.to_numeric(out[c],errors="coerce")
    out=out.dropna().drop_duplicates(["timestamp","symbol"],keep="last").sort_values(["timestamp","symbol"])
    if out.empty: raise RuntimeError("V5.6 rejected every locked observation.")
    return out.reset_index(drop=True)

def canonical_frame_hash(frame: pd.DataFrame) -> str:
    normalized=normalize_locked_input(frame)
    csv=normalized.to_csv(index=False,date_format="%Y-%m-%dT%H:%M:%S.%f%z",float_format="%.17g",lineterminator="\n")
    return hashlib.sha256(csv.encode("utf-8")).hexdigest()

def canonical_json_hash(value: dict[str,Any]) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def build_lock_manifest(frame: pd.DataFrame, config: dict[str,Any], provenance: str, upstream_hash: str) -> dict[str,Any]:
    payload={"schema_version":"1.0","stage":"5.6.1","data_sha256":canonical_frame_hash(frame),"config":config,"config_sha256":canonical_json_hash(config),"upstream_contract_sha256":upstream_hash,"provenance":provenance,"rows":len(frame),"periods":int(frame["timestamp"].nunique()),"symbols":int(frame["symbol"].nunique()),"immutable":True}
    payload["lock_id"]=canonical_json_hash(payload)
    return payload

def simulate_locked(frame: pd.DataFrame,long_fraction:float,cost_bps:float)->tuple[pd.DataFrame,pd.DataFrame]:
    if not 0<long_fraction<=.5: raise ValueError("long_fraction must be in (0, 0.5].")
    prior={}; returns=[]; positions=[]
    for timestamp,section in frame.groupby("timestamp",sort=True,observed=True):
        section=section.copy(); pct=section["alpha__ensemble"].rank(pct=True,method="first")
        long=pct>=1-long_fraction; short=pct<=long_fraction; section["weight"]=0.0
        if long.any(): section.loc[long,"weight"]=.5/int(long.sum())
        if short.any(): section.loc[short,"weight"]=-.5/int(short.sum())
        current=dict(zip(section.symbol,section.weight)); names=set(prior)|set(current)
        turnover=.5*sum(abs(current.get(n,0)-prior.get(n,0)) for n in names)
        gross=float((section.weight*section.forward_return).sum()); cost=turnover*cost_bps/10000
        returns.append({"timestamp":timestamp,"gross_return":gross,"turnover":turnover,"transaction_cost":cost,"net_return":gross-cost,"gross_exposure":float(section.weight.abs().sum()),"net_exposure":float(section.weight.sum())})
        positions.append(section[["timestamp","symbol","alpha__ensemble","forward_return","weight"]]); prior=current
    return pd.DataFrame(returns),pd.concat(positions,ignore_index=True)

def validation_metrics(returns:pd.DataFrame)->dict[str,Any]:
    net=returns.net_return; vol=float(net.std(ddof=0)); mean=float(net.mean()); equity=(1+net).cumprod(); draw=float((equity/equity.cummax()-1).min())
    return {"period_count":len(net),"cumulative_net_return":float(equity.iloc[-1]-1),"annualized_sharpe":float(mean/vol*np.sqrt(252)) if vol>0 else 0.0,"maximum_drawdown":draw,"positive_period_fraction":float((net>0).mean()),"mean_turnover":float(returns.turnover.mean()),"total_transaction_cost":float(returns.transaction_cost.sum())}

def decide(metrics:dict[str,Any],config:dict[str,Any])->dict[str,Any]:
    checks={"minimum_periods":metrics["period_count"]>=config["minimum_periods"],"positive_net_return":metrics["cumulative_net_return"]>config["minimum_net_return"],"minimum_sharpe":metrics["annualized_sharpe"]>=config["minimum_sharpe"],"maximum_drawdown":metrics["maximum_drawdown"]>=-abs(config["maximum_drawdown"]),"turnover_limit":metrics["mean_turnover"]<=config["maximum_mean_turnover"]}
    return {"checks":checks,"passed":all(checks.values())}

