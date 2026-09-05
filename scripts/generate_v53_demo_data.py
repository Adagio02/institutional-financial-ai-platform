from pathlib import Path
import numpy as np
import pandas as pd


def main() -> None:
    output = Path("data/research/v53")
    output.mkdir(parents=True, exist_ok=True)
    symbols = ["AAPL", "MSFT", "AMZN", "NVDA", "SPY", "QQQ"]
    dates = pd.bdate_range("2026-01-02", periods=12, tz="UTC") + pd.Timedelta(hours=21)
    fundamental_rows, event_rows, news_rows, price_rows = [], [], [], []
    rng = np.random.default_rng(53)
    for index, symbol in enumerate(symbols):
        for quarter in range(3):
            available = dates[min(quarter * 4, len(dates) - 1)] - pd.Timedelta(hours=1)
            revenue = 1000.0 * (1 + 0.05 * index) * (1 + 0.04 * quarter)
            income = revenue * (0.08 + index * 0.005)
            fundamental_rows.append({
                "symbol": symbol, "available_at": available, "period_end": available - pd.Timedelta(days=30),
                "revenue": revenue, "net_income": income, "operating_cash_flow": income * 1.15,
                "total_assets": revenue * 2.5, "total_equity": revenue * 1.2,
                "market_cap": revenue * (12 + index),
            })
        for period, timestamp in enumerate(dates):
            event_rows.append({
                "symbol": symbol, "available_at": timestamp - pd.Timedelta(hours=2),
                "event_type": "earnings", "actual": 1.0 + 0.02 * index + 0.01 * period,
                "consensus": 1.0 + 0.01 * period,
            })
            news_rows.append({
                "symbol": symbol, "published_at": timestamp - pd.Timedelta(hours=1),
                "headline": f"DEMO {symbol} research headline {period}",
                "sentiment": np.sin(period / 2 + index) * 0.7,
            })
            price_rows.append({
                "timestamp": timestamp, "symbol": symbol,
                "close": 100 + 5 * index + period * (0.2 + index * 0.03) + rng.normal(0, 0.25),
            })
    pd.DataFrame(fundamental_rows).to_csv(output / "fundamentals.csv", index=False)
    pd.DataFrame(event_rows).to_csv(output / "events.csv", index=False)
    pd.DataFrame(news_rows).to_csv(output / "news.csv", index=False)
    pd.DataFrame(price_rows).to_csv(output / "prices.csv", index=False)
    print(f"Created synthetic V5.3 smoke-test data in {output}")
    print("This data cannot qualify a champion.")


if __name__ == "__main__":
    main()

