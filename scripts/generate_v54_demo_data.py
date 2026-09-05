from pathlib import Path
import numpy as np
import pandas as pd


def main():
    output = Path("data/research/v54")
    output.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(54)
    symbols = ["AAPL", "MSFT", "AMZN", "NVDA", "SPY", "QQQ"]
    dates = pd.bdate_range("2026-01-02", periods=14, tz="UTC")
    base = []
    for t, date in enumerate(dates):
        for i, symbol in enumerate(symbols):
            latent = (i - 2.5) / 3 + np.sin(t / 3 + i)
            base.append({"timestamp": date, "symbol": symbol, "close": 100 + i * 8 + t * (0.1 + i * 0.025) + rng.normal(0, .15), "latent": latent})
    base = pd.DataFrame(base)
    target = base[["timestamp", "symbol", "close"]]
    target.to_csv(output / "target.csv", index=False)
    specifications = {
        "price": ["momentum", "reversal"], "microstructure": ["imbalance", "spread"],
        "options": ["skew", "term"], "fundamental": ["value", "quality", "news"],
    }
    for family, names in specifications.items():
        frame = base[["timestamp", "symbol"]].copy()
        for index, name in enumerate(names):
            frame[f"alpha__{name}"] = base["latent"] * (0.7 - index * .1) + rng.normal(0, .35, len(base))
        frame.to_csv(output / f"{family}.csv", index=False)
    print(f"Created synthetic V5.4 smoke-test panels in {output}")
    print("This data cannot qualify a champion.")


if __name__ == "__main__":
    main()

