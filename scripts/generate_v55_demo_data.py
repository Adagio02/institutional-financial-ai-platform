from pathlib import Path
import numpy as np
import pandas as pd

def main():
    output = Path("data/research/v55"); output.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(55); rows=[]; symbols=["AAPL","MSFT","AMZN","NVDA","SPY","QQQ"]
    dates=pd.bdate_range("2026-01-02", periods=20, tz="UTC")
    for t,date in enumerate(dates):
        alpha=rng.normal(size=len(symbols)); future=0.002*alpha+rng.normal(0,0.001,len(symbols))
        for symbol,a,r in zip(symbols,alpha,future): rows.append({"timestamp":date,"symbol":symbol,"alpha__ensemble":a,"forward_return":r})
    pd.DataFrame(rows).to_csv(output/"ensemble.csv",index=False)
    print(f"Created synthetic V5.5 smoke-test data: {output/'ensemble.csv'}")
    print("This data cannot enter locked validation or qualify a champion.")
if __name__ == "__main__": main()
