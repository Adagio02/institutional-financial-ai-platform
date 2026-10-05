import argparse,json
from pathlib import Path
import pandas as pd

p=argparse.ArgumentParser();p.add_argument("--protocol",required=True);a=p.parse_args()
protocol=json.loads(Path(a.protocol).read_text());start=pd.Timestamp(protocol["prospective_lock_start"]);today=pd.Timestamp.now(tz="UTC").normalize()
available=max(0,len(pd.bdate_range(start,today)))
print(json.dumps({"prospective_lock_start":start.isoformat(),"today":today.isoformat(),"available_business_days":available,
 "ready_for_minimum_52_period_lock":available>=260},indent=2))
