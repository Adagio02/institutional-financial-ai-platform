from __future__ import annotations
import numpy as np
import pandas as pd

V473_FEATURE_COLUMNS = [
    "return_1","return_5","return_15","return_30","return_60",
    "volatility_5","volatility_15","volatility_30","volatility_60",
    "relative_volume_20","market_excess_return_1","benchmark_excess_return_1",
    "market_excess_return_5","market_excess_return_15",
    "market_excess_return_30","market_excess_return_60",
    "cross_sectional_rank_return_15","cross_sectional_rank_volume",
]

def add_cross_sectional_targets(
    panel: pd.DataFrame, *, horizon_bars: int = 30
) -> pd.DataFrame:
    out = panel.copy().sort_values(["symbol","timestamp"])
    future = (
        out.groupby("symbol", sort=False)["close"].shift(-horizon_bars) / out["close"] - 1.0
    )
    out["future_return"] = future

    benchmark_future = (
        out[["timestamp","symbol","future_return"]]
        .rename(columns={"symbol":"benchmark","future_return":"benchmark_future_return"})
    )
    out = out.merge(benchmark_future, on=["timestamp","benchmark"], how="left")

    spy_future = (
        out.loc[out["symbol"] == "SPY", ["timestamp","future_return"]]
        .rename(columns={"future_return":"spy_future_return"})
    )
    out = out.merge(spy_future, on="timestamp", how="left")
    out["future_market_excess_return"] = out["future_return"] - out["spy_future_return"]
    out["future_benchmark_excess_return"] = out["future_return"] - out["benchmark_future_return"]
    out["target_cross_sectional_rank"] = out.groupby("timestamp")[
        "future_benchmark_excess_return"
    ].rank(pct=True)
    out.replace([np.inf,-np.inf], np.nan, inplace=True)
    return out
