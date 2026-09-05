from pathlib import Path
import numpy as np,pandas as pd
out=Path("data/research/v58");out.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(58);symbols=["AAPL","MSFT","AMZN","NVDA","SPY","QQQ"];prices=np.array([180.,410.,190.,220.,650.,570.]);rows=[]
for d in pd.bdate_range("2026-06-01",periods=12,tz="UTC"):
 a=rng.normal(size=6);prices=prices*(1+.002*a+rng.normal(0,.0005,6))
 for s,x,p in zip(symbols,a,prices):rows.append({"timestamp":d,"symbol":s,"alpha__ensemble":x,"price":p})
pd.DataFrame(rows).to_csv(out/"snapshots.csv",index=False);print("Created synthetic V5.8 shadow snapshots. No orders can be submitted.")
