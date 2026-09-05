from pathlib import Path
import numpy as np,pandas as pd
out=Path("data/research/v57");out.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(57);rows=[];symbols=["AAPL","MSFT","AMZN","NVDA","SPY","QQQ"]
for d in pd.bdate_range("2026-05-01",periods=10,tz="UTC"):
 a=rng.normal(size=6)
 for s,x in zip(symbols,a):rows.append({"timestamp":d,"symbol":s,"alpha__ensemble":x,"forward_return":.002*x+rng.normal(0,.0003)})
pd.DataFrame(rows).to_csv(out/"final_input.csv",index=False);print("Created synthetic V5.7 smoke data. It cannot open V5.8.")
