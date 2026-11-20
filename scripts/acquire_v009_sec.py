from __future__ import annotations

import argparse,json,os,time
from pathlib import Path
import pandas as pd
import requests

TICKERS="https://www.sec.gov/files/company_tickers.json"
FACTS="https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
SUBMISSIONS="https://data.sec.gov/submissions/CIK{cik:010d}.json"
CONCEPTS={
 "revenue":["RevenueFromContractWithCustomerExcludingAssessedTax","Revenues","SalesRevenueNet"],
 "net_income":["NetIncomeLoss"],"assets":["Assets"],"liabilities":["Liabilities"],
 "equity":["StockholdersEquity","StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
 "operating_cash_flow":["NetCashProvidedByUsedInOperatingActivities"],
 "capex":["PaymentsToAcquirePropertyPlantAndEquipment"],"inventory":["InventoryNet"],
 "gross_profit":["GrossProfit"],"operating_income":["OperatingIncomeLoss"],
 "shares":["CommonStockSharesOutstanding","EntityCommonStockSharesOutstanding"],
}

def get_json(url,headers):
 for attempt in range(5):
  response=requests.get(url,headers=headers,timeout=60)
  if response.status_code in (429,403) and attempt<4:time.sleep(2**attempt);continue
  response.raise_for_status();return response.json()
 raise RuntimeError(f"Unable to retrieve {url}")

def fact_rows(symbol,cik,payload):
 facts=payload.get("facts",{}).get("us-gaap",{});rows=[]
 for canonical,aliases in CONCEPTS.items():
  concept=next((facts[a] for a in aliases if a in facts),None)
  if not concept:continue
  preferred=("shares",) if canonical=="shares" else ("USD",)
  units=concept.get("units",{});records=next((units[u] for u in preferred if u in units),None)
  if records is None and units:records=next(iter(units.values()))
  for item in records or []:
   if item.get("form") not in {"10-K","10-Q","10-K/A","10-Q/A"}:continue
   if not item.get("filed") or not item.get("end") or "val" not in item:continue
   rows.append({"symbol":symbol,"cik":cik,"available_at":item["filed"],"period_end":item["end"],
    "form":item.get("form"),"accession":item.get("accn"),"fiscal_year":item.get("fy"),
    "fiscal_period":item.get("fp"),"concept":canonical,"value":item["val"]})
 return rows

def submission_rows(symbol,cik,payload):
 recent=payload.get("filings",{}).get("recent",{});rows=[]
 forms=recent.get("form",[])
 for i,form in enumerate(forms):
  if form not in {"10-K","10-Q","8-K","10-K/A","10-Q/A","8-K/A"}:continue
  rows.append({"symbol":symbol,"cik":cik,"available_at":recent["filingDate"][i],
   "event_type":form,"accession":recent["accessionNumber"][i],
   "report_date":recent.get("reportDate",[None]*len(forms))[i]})
 return rows

def main():
 p=argparse.ArgumentParser();p.add_argument("--universe",required=True);p.add_argument("--output",required=True)
 p.add_argument("--cache",default="data/cache/sec");a=p.parse_args()
 user_agent=os.getenv("SEC_USER_AGENT","").strip()
 if "@" not in user_agent:raise RuntimeError("Set SEC_USER_AGENT to 'Your Name your-email@example.com'")
 headers={"User-Agent":user_agent,"Accept-Encoding":"gzip, deflate","Host":"data.sec.gov"}
 ticker_headers={k:v for k,v in headers.items() if k!="Host"}
 mapping=get_json(TICKERS,ticker_headers);ticker_map={v["ticker"].upper():int(v["cik_str"]) for v in mapping.values()}
 symbols=pd.read_csv(a.universe).symbol.astype(str).str.upper().tolist();facts=[];events=[];errors=[]
 cache=Path(a.cache);cache.mkdir(parents=True,exist_ok=True)
 for number,symbol in enumerate(symbols,1):
  cik=ticker_map.get(symbol)
  if cik is None:errors.append({"symbol":symbol,"error":"CIK not found"});continue
  try:
   cf=get_json(FACTS.format(cik=cik),headers);sub=get_json(SUBMISSIONS.format(cik=cik),headers)
   (cache/f"{symbol}_companyfacts.json").write_text(json.dumps(cf),encoding="utf-8")
   (cache/f"{symbol}_submissions.json").write_text(json.dumps(sub),encoding="utf-8")
   facts.extend(fact_rows(symbol,cik,cf));events.extend(submission_rows(symbol,cik,sub))
   print(f"{number}/{len(symbols)} {symbol}: facts={len(facts)} events={len(events)}")
  except Exception as exc:errors.append({"symbol":symbol,"error":str(exc)})
  time.sleep(.15)
 out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 long=pd.DataFrame(facts)
 if long.empty:raise RuntimeError("No SEC facts acquired")
 long["available_at"]=pd.to_datetime(long.available_at,utc=True);long["period_end"]=pd.to_datetime(long.period_end,utc=True)
 long=long.sort_values(["symbol","available_at","period_end"]).drop_duplicates(["symbol","available_at","concept"],keep="last")
 wide=long.pivot_table(index=["symbol","available_at"],columns="concept",values="value",aggfunc="last").reset_index()
 wide.columns.name=None;wide=wide.sort_values(["symbol","available_at"])
 wide.to_parquet(out/"fundamentals.parquet",index=False)
 event_frame=pd.DataFrame(events);event_frame["available_at"]=pd.to_datetime(event_frame.available_at,utc=True)
 event_frame.sort_values(["symbol","available_at"]).to_parquet(out/"filing_events.parquet",index=False)
 pd.DataFrame(errors).to_json(out/"acquisition_errors.json",orient="records",indent=2)
 print(f"Saved {len(wide)} point-in-time fundamental rows and {len(event_frame)} filing events to {out}")

if __name__=="__main__":main()
