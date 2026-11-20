from __future__ import annotations

import argparse, hashlib, json, os, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import requests

AV = "https://www.alphavantage.co/query"
ALPACA = "https://data.alpaca.markets/v2/stocks/bars"
SEC_TICKERS = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

TAGS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "total_assets": ["Assets"],
    "total_equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
}

def need(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value: raise RuntimeError(f"Required environment variable is missing: {name}")
    return value

def get_json(url, *, params=None, headers=None, attempts=5):
    for n in range(attempts):
        r = requests.get(url, params=params, headers=headers, timeout=60)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and (data.get("Note") or data.get("Information")):
                raise RuntimeError(data.get("Note") or data.get("Information"))
            return data
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** n); continue
        raise RuntimeError(f"GET {r.url} failed: HTTP {r.status_code}: {r.text[:300]}")
    raise RuntimeError(f"GET {url} failed after retries")

def alpaca_prices(symbols, start, end):
    headers={"APCA-API-KEY-ID":need("APCA_API_KEY_ID"),"APCA-API-SECRET-KEY":need("APCA_API_SECRET_KEY")}
    rows=[]; token=None
    while True:
        params={"symbols":",".join(symbols),"timeframe":"1Day","start":start,"end":end,"limit":10000,"feed":"iex","adjustment":"all"}
        if token: params["page_token"]=token
        data=get_json(ALPACA,params=params,headers=headers)
        for symbol,bars in data.get("bars",{}).items():
            rows += [{"timestamp":b["t"],"symbol":symbol,"close":b["c"]} for b in bars]
        token=data.get("next_page_token")
        if not token: break
    out=pd.DataFrame(rows)
    if out.empty: raise RuntimeError("Alpaca returned no price bars")
    out["timestamp"]=pd.to_datetime(out["timestamp"],utc=True)
    return out.sort_values(["timestamp","symbol"]).drop_duplicates(["timestamp","symbol"])

def av(symbol, function, **extra):
    params={"function":function,"symbol":symbol,"apikey":need("ALPHA_VANTAGE_API_KEY"),**extra}
    return get_json(AV,params=params)

def earnings_events(symbols):
    rows=[]
    for i,symbol in enumerate(symbols):
        data=av(symbol,"EARNINGS")
        for x in data.get("quarterlyEarnings",[]):
            if x.get("reportedDate") and x.get("reportedEPS") not in (None,"None") and x.get("estimatedEPS") not in (None,"None"):
                rows.append({"symbol":symbol,"available_at":x["reportedDate"],"event_type":"earnings","actual":x["reportedEPS"],"consensus":x["estimatedEPS"]})
        if i+1<len(symbols): time.sleep(float(os.getenv("FINAI_AV_DELAY_SECONDS","12")))
    out=pd.DataFrame(rows)
    if out.empty: raise RuntimeError("Alpha Vantage returned no usable earnings events")
    return out

def news(symbols,start,end):
    rows=[]
    tf=pd.Timestamp(start).strftime("%Y%m%dT%H%M"); tt=pd.Timestamp(end).strftime("%Y%m%dT%H%M")
    for i,symbol in enumerate(symbols):
        data=get_json(AV,params={"function":"NEWS_SENTIMENT","tickers":symbol,"time_from":tf,"time_to":tt,"sort":"EARLIEST","limit":1000,"apikey":need("ALPHA_VANTAGE_API_KEY")})
        for item in data.get("feed",[]):
            score=None
            for ts in item.get("ticker_sentiment",[]):
                if ts.get("ticker","").upper()==symbol: score=ts.get("ticker_sentiment_score"); break
            if score is not None and item.get("title") and item.get("time_published"):
                rows.append({"symbol":symbol,"published_at":item["time_published"],"headline":item["title"],"sentiment":score})
        if i+1<len(symbols): time.sleep(float(os.getenv("FINAI_AV_DELAY_SECONDS","12")))
    out=pd.DataFrame(rows)
    if out.empty: raise RuntimeError("Alpha Vantage returned no usable news")
    return out

def sec_units(facts, tags, unit="USD"):
    usgaap=facts.get("facts",{}).get("us-gaap",{})
    for tag in tags:
        units=usgaap.get(tag,{}).get("units",{})
        values=units.get(unit)
        if values: return values
    return []

def match_value(values, end, filed):
    eligible = [
        item
        for item in values
        if item.get("form") in {"10-Q", "10-K", "10-Q/A", "10-K/A"}
        and item.get("filed")
        and item.get("end")
        and item.get("val") is not None
        and item.get("filed", "") <= filed
    ]

    exact = [
        item
        for item in eligible
        if item.get("end") == end
    ]

    if exact:
        selected = sorted(
            exact,
            key=lambda item: (
                item.get("filed", ""),
                item.get("fy", 0) or 0,
            ),
            reverse=True,
        )[0]
        return selected.get("val")

    prior_period = [
        item
        for item in eligible
        if item.get("end", "") <= end
    ]

    if not prior_period:
        return None

    selected = sorted(
        prior_period,
        key=lambda item: (
            item.get("end", ""),
            item.get("filed", ""),
            item.get("fy", 0) or 0,
        ),
        reverse=True,
    )[0]

    return selected.get("val")

def shares_values(facts):
    result=[]
    for namespace in ("dei","us-gaap"):
        for tag in ("EntityCommonStockSharesOutstanding","CommonStocksIncludingAdditionalPaidInCapital"):
            result += facts.get("facts",{}).get(namespace,{}).get(tag,{}).get("units",{}).get("shares",[])
    return result

def fundamentals(symbols,prices):
    ua={"User-Agent":need("FINAI_SEC_USER_AGENT"),"Accept-Encoding":"gzip, deflate"}
    mapping=get_json(SEC_TICKERS,headers=ua)
    ciks={v["ticker"].upper():int(v["cik_str"]) for v in mapping.values()}
    rows=[]
    for symbol in symbols:
        if symbol not in ciks: raise RuntimeError(f"SEC CIK not found for {symbol}")
        facts=get_json(SEC_FACTS.format(cik=ciks[symbol]),headers=ua)
        anchors=sec_units(facts,TAGS["revenue"])
        metrics={k:sec_units(facts,v) for k,v in TAGS.items()}
        shares=shares_values(facts)
        for a in anchors:
            if a.get("form") not in {"10-Q","10-K","10-Q/A","10-K/A"} or not a.get("filed") or not a.get("end"): continue
            row={"symbol":symbol,"available_at":a["filed"],"period_end":a["end"],"revenue":a.get("val")}
            for key in ("net_income","operating_cash_flow","total_assets","total_equity"):
                row[key]=match_value(metrics[key],a["end"],a["filed"])
            sh=match_value(shares,a["end"],a["filed"])
            if sh is None:
                prior=[x for x in shares if x.get("filed","")<=a["filed"] and x.get("val")]
                sh=sorted(prior,key=lambda x:x.get("filed",""),reverse=True)[0].get("val") if prior else None
            section=prices[(prices.symbol==symbol)&(prices.timestamp<=pd.Timestamp(a["filed"],tz="UTC"))]
            close=float(section.iloc[-1].close) if len(section) else None
            row["market_cap"]=float(sh)*close if sh and close else None
            rows.append(row)
        time.sleep(.12)
    out=pd.DataFrame(rows).dropna()
    if out.empty: raise RuntimeError("SEC facts produced no complete fundamental rows; inspect selected symbols/date range")
    return out.sort_values(["available_at","symbol"]).drop_duplicates(["symbol","period_end","available_at"])

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(); p.add_argument("--symbols",default="AAPL,MSFT,AMZN,NVDA,META,GOOGL"); p.add_argument("--start",default="2023-01-01"); p.add_argument("--end",default=datetime.now(timezone.utc).date().isoformat()); p.add_argument("--output",default="data/research/v53"); a=p.parse_args()
    symbols=[x.strip().upper() for x in a.symbols.split(",") if x.strip()]
    out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
    prices=alpaca_prices(symbols,a.start,a.end)
    events = earnings_events(symbols)
    time.sleep(float(os.getenv("FINAI_AV_DELAY_SECONDS", "15")))
    news_frame = news(symbols, a.start, a.end)
    frames = {"prices": prices, "events": events, "news": news_frame}
    frames["fundamentals"]=fundamentals(symbols,prices)
    required={"prices":{"timestamp","symbol","close"},"events":{"symbol","available_at","event_type","actual","consensus"},"news":{"symbol","published_at","headline","sentiment"},"fundamentals":{"symbol","available_at","period_end","revenue","net_income","operating_cash_flow","total_assets","total_equity","market_cap"}}
    files={}
    for name,frame in frames.items():
        missing=required[name]-set(frame.columns)
        if missing: raise RuntimeError(f"{name} missing columns: {sorted(missing)}")
        path=out/f"{name}.parquet"; frame.to_parquet(path,index=False); files[name]={"path":str(path),"rows":len(frame),"sha256":sha(path)}
    manifest={"schema_version":"1.0","provenance":"real_external_api","collected_at":datetime.now(timezone.utc).isoformat(),"symbols":symbols,"range":{"start":a.start,"end":a.end},"sources":{"prices":"Alpaca IEX adjusted daily bars","fundamentals":"SEC EDGAR Company Facts","events":"Alpha Vantage Earnings","news":"Alpha Vantage News Sentiment"},"files":files}
    (out/"source_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps(manifest,indent=2))

if __name__=="__main__": main()

