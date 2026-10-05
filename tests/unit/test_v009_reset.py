import numpy as np
import pandas as pd
from importlib.util import module_from_spec,spec_from_file_location
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def load(name,file):
 spec=spec_from_file_location(name,ROOT/"scripts"/file);module=module_from_spec(spec);spec.loader.exec_module(module);return module

def test_sec_parser_preserves_filing_availability():
 module=load("sec","acquire_v009_sec.py")
 payload={"facts":{"us-gaap":{"Assets":{"units":{"USD":[{"val":10,"end":"2023-12-31","filed":"2024-02-15","form":"10-K","accn":"x"}]}}}}}
 rows=module.fact_rows("AAA",1,payload)
 assert rows[0]["available_at"]=="2024-02-15" and rows[0]["period_end"]=="2023-12-31"

def test_price_features_are_lagged():
 module=load("panel","build_v009_panel.py")
 dates=pd.date_range("2024-01-01",periods=30,tz="UTC")
 close=np.arange(100.,130.)
 frame=pd.DataFrame({"timestamp":dates,"close":close,"volume":1000.,"high":close+1,"low":close-1})
 result=module.price_features(frame)
 assert pd.isna(result.loc[0,"return_lag_1"])
 assert np.isclose(result.loc[2,"return_lag_1"],close[1]/close[0]-1)

def test_universe_has_at_least_one_hundred_symbols_and_sector_breadth():
 universe=pd.read_csv(ROOT/"config"/"v009_universe.csv")
 assert universe.symbol.nunique()>=100 and universe.sector.nunique()>=10

def test_point_in_time_join_never_uses_later_filing():
 module=load("panel_pit","build_v009_panel.py")
 dates=pd.to_datetime(["2024-01-10","2024-02-20"],utc=True)
 left=pd.DataFrame({"timestamp":dates,"symbol":["AAA","AAA"],"close":[10.,11.]})
 right=pd.DataFrame({"available_at":pd.to_datetime(["2024-02-15"],utc=True),"symbol":["AAA"],"assets":[100.]})
 joined=module.asof_by_symbol(left,right)
 assert pd.isna(joined.loc[0,"assets"]) and joined.loc[1,"assets"]==100.
