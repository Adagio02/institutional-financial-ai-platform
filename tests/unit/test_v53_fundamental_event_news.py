import pandas as pd

from finai.domain.fundamental.v53_research import (
    SIGNAL_COLUMNS, build_point_in_time_features, build_signals,
    normalize_events, normalize_fundamentals, normalize_news, normalize_prices,
    qualify_signals,
)


def _frames():
    symbols = ["A", "B", "C", "D", "E", "F"]
    dates = pd.date_range("2026-01-05", periods=6, freq="D", tz="UTC")
    fundamentals, events, news, prices = [], [], [], []
    for i, symbol in enumerate(symbols):
        fundamentals.append({
            "symbol": symbol, "available_at": dates[0] - pd.Timedelta(days=1),
            "period_end": dates[0] - pd.Timedelta(days=30), "revenue": 100 + i,
            "net_income": 8 + i, "operating_cash_flow": 10 + i,
            "total_assets": 200 + i, "total_equity": 80 + i, "market_cap": 500 + 10 * i,
        })
        for j, date in enumerate(dates):
            events.append({"symbol": symbol, "available_at": date, "event_type": "earnings", "actual": 1+i/10, "consensus": 1})
            news.append({"symbol": symbol, "published_at": date, "headline": f"{symbol}-{j}", "sentiment": (i-2)/4})
            prices.append({"timestamp": date, "symbol": symbol, "close": 100+i*5+j*(i+1)/10})
    return (
        normalize_fundamentals(pd.DataFrame(fundamentals)),
        normalize_events(pd.DataFrame(events)), normalize_news(pd.DataFrame(news)),
        normalize_prices(pd.DataFrame(prices)),
    )


def test_v53_pipeline_has_no_lookahead_and_all_signals():
    features = build_point_in_time_features(*_frames())
    assert not (features["source_available_at"] > features["timestamp"]).any()
    signals = build_signals(features)
    assert set(SIGNAL_COLUMNS).issubset(signals.columns)
    qualified = qualify_signals(signals)
    assert len(qualified) == len(SIGNAL_COLUMNS)
    by_name = {item["signal_column"]: item for item in qualified}
    assert by_name["alpha__event_surprise"]["period_count"] >= 3
    assert by_name["alpha__news_sentiment"]["period_count"] >= 3
