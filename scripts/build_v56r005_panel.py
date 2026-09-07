from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def read_optional(path: str | None) -> pd.DataFrame | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    return pd.read_csv(p) if p.suffix.lower() == ".csv" else pd.read_parquet(p)


def point_in_time_join(panel: pd.DataFrame, extra: pd.DataFrame | None, prefix: str) -> pd.DataFrame:
    if extra is None or extra.empty:
        return panel
    time_candidates = ["available_at", "published_at", "filed_at", "timestamp"]
    time_col = next((c for c in time_candidates if c in extra.columns), None)
    if time_col is None or "symbol" not in extra:
        raise ValueError(f"{prefix} data requires symbol and one of {time_candidates}")
    right = extra.copy()
    right["symbol"] = right.symbol.astype(str).str.upper()
    right[time_col] = pd.to_datetime(right[time_col], utc=True)
    numeric = [c for c in right.select_dtypes(include=[np.number]).columns if c not in {"close", "forward_return"}]
    if not numeric:
        return panel
    right = right[["symbol", time_col] + numeric].rename(columns={c: f"{prefix}_{c}" for c in numeric})
    parts = []
    for symbol, left_part in panel.groupby("symbol", observed=True):
        rp = right[right.symbol == symbol].drop(columns="symbol").sort_values(time_col)
        lp = left_part.sort_values("timestamp")
        if rp.empty:
            parts.append(lp)
        else:
            parts.append(pd.merge_asof(lp, rp, left_on="timestamp", right_on=time_col, direction="backward").drop(columns=time_col))
    return pd.concat(parts, ignore_index=True)


def features(section: pd.DataFrame) -> pd.DataFrame:
    s = section.sort_values("timestamp").copy()
    c, v = s.close.astype(float), s.volume.astype(float)
    r = c.pct_change(fill_method=None)
    s["return_lag_1"] = r.shift(1)
    for horizon in (5, 21, 63, 126):
        s[f"momentum_{horizon}"] = c.pct_change(horizon, fill_method=None).shift(1)
    s["volatility"] = r.rolling(20, min_periods=10).std().shift(1)
    s["volatility_63"] = r.rolling(63, min_periods=30).std().shift(1)
    s["vol_scaled_momentum"] = s.momentum_21 / s.volatility.replace(0, np.nan)
    dollar = c * v
    s["log_dollar_volume"] = np.log1p(dollar).rolling(20, min_periods=10).mean().shift(1)
    s["volume_change_20"] = (v / v.rolling(20, min_periods=10).mean() - 1).shift(1)
    s["amihud_20"] = (r.abs() / dollar.replace(0, np.nan)).rolling(20, min_periods=10).mean().shift(1)
    s["range_20"] = ((s.high - s.low) / c).rolling(20, min_periods=10).mean().shift(1)
    return s


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--bars", required=True); p.add_argument("--universe", required=True)
    p.add_argument("--output", required=True); p.add_argument("--fundamentals")
    p.add_argument("--events"); p.add_argument("--news"); p.add_argument("--minimum-symbols", type=int, default=30)
    a = p.parse_args()
    bars, universe = pd.read_parquet(a.bars), pd.read_csv(a.universe)
    bars["timestamp"] = pd.to_datetime(bars.timestamp, utc=True)
    bars["symbol"] = bars.symbol.astype(str).str.upper()
    universe["symbol"] = universe.symbol.astype(str).str.upper()
    universe["effective_from"] = pd.to_datetime(universe.effective_from, utc=True)
    universe["effective_to"] = pd.to_datetime(universe.effective_to, utc=True)
    benchmark = bars[bars.symbol == "SPY"][["timestamp", "close"]].sort_values("timestamp")
    benchmark["market_return"] = benchmark.close.pct_change(fill_method=None)
    stocks = bars[bars.symbol.isin(universe.symbol)].merge(universe, on="symbol", how="inner")
    stocks = stocks[(stocks.timestamp >= stocks.effective_from) & (stocks.timestamp <= stocks.effective_to)]
    panel = pd.concat(
        [features(section) for _, section in stocks.groupby("symbol", observed=True)],
        ignore_index=True,
    )
    panel = panel.merge(benchmark[["timestamp", "market_return"]], on="timestamp", how="left")
    raw_return = panel.groupby("symbol", observed=True).close.pct_change(fill_method=None)
    panel["raw_return"] = raw_return
    beta_parts = []
    for _, section in panel.groupby("symbol", observed=True):
        market = section.market_return
        stock = section.raw_return
        beta = (
            stock.rolling(126, min_periods=63).cov(market)
            / market.rolling(126, min_periods=63).var()
        ).shift(1)
        beta_parts.append(beta)
    panel["beta"] = pd.concat(beta_parts).sort_index()
    panel["sector_return"] = raw_return.groupby([panel.timestamp, panel.sector]).transform("mean")
    panel["residual_return"] = raw_return - panel.beta.fillna(1.0) * panel.market_return - panel.sector_return
    panel["residual_momentum_21"] = panel.groupby("symbol", observed=True).residual_return.transform(
        lambda r: (1 + r).rolling(21, min_periods=15).apply(np.prod, raw=True).shift(1) - 1
    )
    panel = point_in_time_join(panel, read_optional(a.fundamentals), "fundamental")
    panel = point_in_time_join(panel, read_optional(a.events), "event")
    panel = point_in_time_join(panel, read_optional(a.news), "news")
    feature_columns = [c for c in panel.select_dtypes(include=[np.number]).columns if c not in {"open","high","low","close","volume","trade_count","vwap","raw_return","market_return","sector_return","residual_return"}]
    for column in feature_columns:
        panel[f"rank_{column}"] = panel.groupby("timestamp", observed=True)[column].rank(pct=True) - .5
    # Keep close solely for label construction. Current-bar values and helper
    # returns are not eligible predictors because execution at that same close
    # would be an unrealistic timing assumption.
    panel = panel.drop(
        columns=[
            "open", "high", "low", "volume", "trade_count", "vwap",
            "raw_return", "market_return", "sector_return", "residual_return",
            "effective_from", "effective_to",
        ],
        errors="ignore",
    )
    panel = panel.replace([np.inf, -np.inf], np.nan)
    counts = panel.groupby("timestamp").symbol.transform("nunique")
    panel = panel[counts >= a.minimum_symbols].sort_values(["timestamp", "symbol"])
    if panel.empty: raise RuntimeError(f"No dates contain at least {a.minimum_symbols} symbols")
    output = Path(a.output); output.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(output, index=False)
    print(f"Saved panel: {output}")
    print(f"Rows={len(panel):,}; periods={panel.timestamp.nunique()}; symbols={panel.symbol.nunique()}; columns={len(panel.columns)}")


if __name__ == "__main__": main()
