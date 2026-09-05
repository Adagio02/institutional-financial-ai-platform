from pathlib import Path
import numpy as np,pandas as pd
out=Path("data/research/v56");out.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(56);rows=[];symbols=["AAPL","MSFT","AMZN","NVDA","SPY","QQQ"]
for date in pd.bdate_range("2026-03-02",periods=10,tz="UTC"):
 a=rng.normal(size=6)
 for s,x in zip(symbols,a):rows.append({"timestamp":date,"symbol":s,"alpha__ensemble":x,"forward_return":.002*x+rng.normal(0,.0003)})
pd.DataFrame(rows).to_csv(out/"locked_input.csv",index=False);print("Created synthetic locked-input smoke data. It cannot open V5.7.")
