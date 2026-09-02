from __future__ import annotations
import numpy as np
import pandas as pd
from finai.domain.learning.v47_universe import V47Universe

def add_relationship_features(panel: pd.DataFrame, universe: V47Universe) -> pd.DataFrame:
    if panel.empty:
        return panel.copy()
    out = panel.copy()
    meta = universe.by_symbol()
    out["sector"] = out["symbol"].map(lambda s: meta[s].sector if s in meta else "Unknown")
    out["benchmark"] = out["symbol"].map(lambda s: meta[s].benchmark if s in meta else "SPY")

    wide = out.pivot(index="timestamp", columns="symbol", values="return_1")
    spy = wide["SPY"] if "SPY" in wide.columns else pd.Series(index=wide.index, dtype=float)
    qqq = wide["QQQ"] if "QQQ" in wide.columns else pd.Series(index=wide.index, dtype=float)
    market = pd.DataFrame({"timestamp": wide.index, "spy_return_1": spy.values, "qqq_return_1": qqq.values})
    out = out.merge(market, on="timestamp", how="left")

    benchmark_long = (
        out[["timestamp","symbol","return_1"]]
        .rename(columns={"symbol":"benchmark","return_1":"benchmark_return_1"})
    )
    out = out.merge(benchmark_long, on=["timestamp","benchmark"], how="left")
    out["market_excess_return_1"] = out["return_1"] - out["spy_return_1"]
    out["benchmark_excess_return_1"] = out["return_1"] - out["benchmark_return_1"]

    for horizon in (5, 15, 30, 60):
        wide_h = out.pivot(index="timestamp", columns="symbol", values=f"return_{horizon}")
        spy_h = wide_h["SPY"] if "SPY" in wide_h.columns else pd.Series(index=wide_h.index, dtype=float)
        lookup = pd.DataFrame({"timestamp":wide_h.index, f"spy_return_{horizon}":spy_h.values})
        out = out.merge(lookup, on="timestamp", how="left")
        out[f"market_excess_return_{horizon}"] = out[f"return_{horizon}"] - out[f"spy_return_{horizon}"]

    out["cross_sectional_rank_return_15"] = out.groupby("timestamp")["return_15"].rank(pct=True)
    out["cross_sectional_rank_volume"] = out.groupby("timestamp")["relative_volume_20"].rank(pct=True)
    out.replace([np.inf,-np.inf], np.nan, inplace=True)
    return out
