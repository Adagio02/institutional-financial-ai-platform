from __future__ import annotations

import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd


def price_features(section):
 s=section.sort_values("timestamp").copy();c=s.close.astype(float);v=s.volume.astype(float);r=c.pct_change(fill_method=None)
 s["price_lag_1"]=c.shift(1);s["return_lag_1"]=r.shift(1)
 for h in (5,21,63,126,252):s[f"momentum_{h}"]=c.pct_change(h,fill_method=None).shift(1)
 s["volatility"]=r.rolling(20,min_periods=10).std().shift(1)
 s["residual_volatility_63"]=r.rolling(63,min_periods=30).std().shift(1)
 s["downside_volatility_63"]=r.where(r<0,0).rolling(63,min_periods=30).std().shift(1)
 s["vol_scaled_momentum"]=s.momentum_126/s.residual_volatility_63.replace(0,np.nan)
 dollar=c*v;s["log_dollar_volume"]=np.log1p(dollar).rolling(20,min_periods=10).mean().shift(1)
 s["volume_shock"]=(v/v.rolling(20,min_periods=10).mean()-1).shift(1)
 s["amihud_20"]=(r.abs()/dollar.replace(0,np.nan)).rolling(20,min_periods=10).mean().shift(1)
 s["range_20"]=((s.high-s.low)/c).rolling(20,min_periods=10).mean().shift(1)
 return s


def asof_by_symbol(left,right,time_col="available_at"):
 parts=[];right=right.copy();right[time_col]=pd.to_datetime(right[time_col],utc=True)
 for symbol,section in left.groupby("symbol",observed=True):
  rp=right[right.symbol==symbol].drop(columns="symbol").sort_values(time_col)
  lp=section.sort_values("timestamp")
  parts.append(lp if rp.empty else pd.merge_asof(lp,rp,left_on="timestamp",right_on=time_col,direction="backward"))
 return pd.concat(parts,ignore_index=True)


def macro_frame(directory):
 root=Path(directory)
 if not root.exists():return None
 frames=[]
 for path in root.glob("*.parquet"):
  f=pd.read_parquet(path)
  if {"date","value"}.issubset(f.columns):
   name=str(f.series_id.iloc[0]) if "series_id" in f and len(f) else path.stem
   frames.append(f[["date","value"]].rename(columns={"value":f"macro_{name}"}).set_index("date"))
 if not frames:return None
 result=pd.concat(frames,axis=1).reset_index();result["date"]=pd.to_datetime(result.date,utc=True)
 numeric=[c for c in result if c.startswith("macro_")];result[numeric]=result[numeric].shift(1)
 return result.sort_values("date")


def main():
 p=argparse.ArgumentParser();p.add_argument("--bars",required=True);p.add_argument("--universe",required=True)
 p.add_argument("--fundamentals",required=True);p.add_argument("--events",required=True);p.add_argument("--output",required=True)
 p.add_argument("--macro-directory",default="data/bronze/fred");p.add_argument("--minimum-symbols",type=int,default=80);p.add_argument("--output-start");a=p.parse_args()
 bars=pd.read_parquet(a.bars);universe=pd.read_csv(a.universe);fund=pd.read_parquet(a.fundamentals);events=pd.read_parquet(a.events)
 bars["timestamp"]=pd.to_datetime(bars.timestamp,utc=True);bars["symbol"]=bars.symbol.astype(str).str.upper()
 universe["symbol"]=universe.symbol.astype(str).str.upper();universe["effective_from"]=pd.to_datetime(universe.effective_from,utc=True);universe["effective_to"]=pd.to_datetime(universe.effective_to,utc=True)
 spy=bars[bars.symbol=="SPY"][["timestamp","close"]].sort_values("timestamp");spy["market_return"]=spy.close.pct_change(fill_method=None);spy["market_trend_200"]=(spy.close/spy.close.rolling(200,min_periods=100).mean()-1).shift(1);spy["market_volatility_20"]=spy.market_return.rolling(20,min_periods=10).std().shift(1)
 stocks=bars[bars.symbol.isin(universe.symbol)].merge(universe,on="symbol",how="inner");stocks=stocks[(stocks.timestamp>=stocks.effective_from)&(stocks.timestamp<=stocks.effective_to)]
 panel=pd.concat([price_features(x) for _,x in stocks.groupby("symbol",observed=True)],ignore_index=True)
 panel=panel.merge(spy[["timestamp","market_return","market_trend_200","market_volatility_20"]],on="timestamp",how="left")
 raw=panel.groupby("symbol",observed=True).close.pct_change(fill_method=None);panel["raw_return"]=raw
 beta=[]
 for _,s in panel.groupby("symbol",observed=True):
  beta.append((s.raw_return.rolling(126,min_periods=63).cov(s.market_return)/s.market_return.rolling(126,min_periods=63).var()).shift(1))
 panel["beta"]=pd.concat(beta).sort_index()
 panel["sector_return"]=raw.groupby([panel.timestamp,panel.sector]).transform("mean")
 panel["residual_return"]=raw-panel.beta.fillna(1)*panel.market_return-panel.sector_return
 panel["residual_momentum_21"]=panel.groupby("symbol",observed=True).residual_return.transform(lambda r:(1+r).rolling(21,min_periods=15).apply(np.prod,raw=True).shift(1)-1)
 panel["residual_momentum_126"]=panel.groupby("symbol",observed=True).residual_return.transform(lambda r:(1+r).rolling(126,min_periods=63).apply(np.prod,raw=True).shift(1)-1)
 fund=fund.sort_values(["symbol","available_at"]);fund["asset_growth"]=fund.groupby("symbol",observed=True).assets.pct_change(fill_method=None) if "assets" in fund else np.nan
 fund["inventory_growth"]=fund.groupby("symbol",observed=True).inventory.pct_change(fill_method=None) if "inventory" in fund else np.nan
 for c in ["net_income","revenue","operating_cash_flow"]:
  if c in fund:fund[f"{c}_stability_4"]=fund.groupby("symbol",observed=True)[c].transform(lambda x:x.rolling(4,min_periods=3).std()/x.abs().rolling(4,min_periods=3).mean().replace(0,np.nan))
 panel=asof_by_symbol(panel,fund)
 market_cap=panel.price_lag_1*panel.get("shares",np.nan)
 panel["earnings_yield"]=panel.get("net_income",np.nan)/market_cap
 panel["book_to_market"]=panel.get("equity",np.nan)/market_cap
 panel["sales_to_price"]=panel.get("revenue",np.nan)/market_cap
 panel["free_cash_flow_yield"]=(panel.get("operating_cash_flow",np.nan)-panel.get("capex",0))/market_cap
 panel["return_on_assets"]=panel.get("net_income",np.nan)/panel.get("assets",np.nan)
 panel["return_on_equity"]=panel.get("net_income",np.nan)/panel.get("equity",np.nan)
 panel["gross_profitability"]=panel.get("gross_profit",np.nan)/panel.get("assets",np.nan)
 panel["operating_margin"]=panel.get("operating_income",np.nan)/panel.get("revenue",np.nan)
 panel["cash_conversion"]=panel.get("operating_cash_flow",np.nan)/panel.get("net_income",np.nan)
 panel["leverage"]=panel.get("liabilities",np.nan)/panel.get("assets",np.nan)
 panel["investment_rate"]=panel.get("capex",np.nan)/panel.get("assets",np.nan)
 panel["days_since_fundamental_filing"]=(panel.timestamp-panel.available_at).dt.total_seconds()/86400
 events=events.sort_values(["symbol","available_at"]);event_parts=[]
 for symbol,left in panel.groupby("symbol",observed=True):
  lp=left.sort_values("timestamp");rp=events[events.symbol==symbol][["available_at","event_type"]].sort_values("available_at")
  joined=lp if rp.empty else pd.merge_asof(lp,rp,left_on="timestamp",right_on="available_at",direction="backward",suffixes=("","_event"))
  event_parts.append(joined)
 panel=pd.concat(event_parts,ignore_index=True)
 if "available_at_event" in panel:panel["days_since_filing_event"]=(panel.timestamp-panel.available_at_event).dt.total_seconds()/86400
 event_type=panel["event_type"].astype(str) if "event_type" in panel else pd.Series("",index=panel.index)
 event_days=panel["days_since_filing_event"] if "days_since_filing_event" in panel else pd.Series(999.,index=panel.index)
 panel["recent_8k_30d"]=(event_type.str.startswith("8-K")&(event_days<=30)).astype(float)
 macro=macro_frame(a.macro_directory)
 if macro is not None:panel=pd.merge_asof(panel.sort_values("timestamp"),macro,left_on="timestamp",right_on="date",direction="backward").drop(columns="date")
 factor_features=["earnings_yield","book_to_market","sales_to_price","free_cash_flow_yield","return_on_assets","return_on_equity","gross_profitability","operating_margin","cash_conversion","leverage","investment_rate","asset_growth","inventory_growth"]
 base_features=[c for c in panel.select_dtypes(include=[np.number]).columns if c not in {"open","high","low","close","volume","trade_count","vwap","price_lag_1","raw_return","market_return","sector_return","residual_return","shares","revenue","net_income","assets","liabilities","equity","operating_cash_flow","capex","inventory","gross_profit","operating_income"}]
 for c in sorted(set(base_features+factor_features)):
  if c not in panel:continue
  panel[f"rank_{c}"]=panel.groupby("timestamp",observed=True)[c].rank(pct=True)-.5
  panel[f"sector_rank_{c}"]=panel.groupby(["timestamp","sector"],observed=True)[c].rank(pct=True)-.5
 drop=["open","high","low","volume","trade_count","vwap","price_lag_1","raw_return","market_return","sector_return","residual_return","effective_from","effective_to","available_at","available_at_event","event_type","classification_provenance","shares","revenue","net_income","assets","liabilities","equity","operating_cash_flow","capex","inventory","gross_profit","operating_income"]
 panel=panel.drop(columns=drop,errors="ignore").replace([np.inf,-np.inf],np.nan)
 counts=panel.groupby("timestamp").symbol.transform("nunique");panel=panel[counts>=a.minimum_symbols].sort_values(["timestamp","symbol"])
 if a.output_start:panel=panel[panel.timestamp>=pd.Timestamp(a.output_start,tz="UTC")]
 if panel.empty:raise RuntimeError(f"No dates have at least {a.minimum_symbols} symbols")
 output=Path(a.output);output.parent.mkdir(parents=True,exist_ok=True);panel.to_parquet(output,index=False)
 coverage={c:float(panel[c].notna().mean()) for c in panel.select_dtypes(include=[np.number]).columns if c!="close"}
 (output.parent/"panel_coverage.json").write_text(json.dumps(coverage,indent=2),encoding="utf-8")
 print(f"Saved {len(panel):,} rows, {panel.symbol.nunique()} symbols, {panel.timestamp.nunique()} periods, {len(panel.columns)} columns to {output}")

if __name__=="__main__":main()
