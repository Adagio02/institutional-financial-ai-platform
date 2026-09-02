from __future__ import annotations
import numpy as np
import pandas as pd

BAR_COLUMNS = ["timestamp","open","high","low","close","volume"]

def normalize_bars(frame: pd.DataFrame, *, symbol: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["timestamp","symbol","open","high","low","close","volume"])
    out = frame.copy()
    aliases = {
        "open_price":"open","high_price":"high","low_price":"low",
        "close_price":"close",
    }
    out = out.rename(columns={k:v for k,v in aliases.items() if k in out.columns})
    missing = [c for c in BAR_COLUMNS if c not in out.columns]
    if missing:
        raise ValueError(f"{symbol}: missing bar columns: {missing}")
    out = out[BAR_COLUMNS].copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True)
    out["symbol"] = symbol.upper()
    for c in ["open","high","low","close","volume"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out.dropna(subset=["timestamp","close"]).sort_values("timestamp").drop_duplicates(
        subset=["timestamp"], keep="last"
    )

def build_point_in_time_panel(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    pieces = [normalize_bars(frame, symbol=symbol) for symbol, frame in frames.items() if not frame.empty]
    if not pieces:
        return pd.DataFrame()
    panel = pd.concat(pieces, ignore_index=True)
    panel = panel.sort_values(["timestamp","symbol"]).reset_index(drop=True)
    panel["return_1"] = panel.groupby("symbol", sort=False)["close"].pct_change()
    for horizon in (5, 15, 30, 60):
        panel[f"return_{horizon}"] = panel.groupby("symbol", sort=False)["close"].pct_change(horizon)
        panel[f"volatility_{horizon}"] = (
            panel.groupby("symbol", sort=False)["return_1"]
            .transform(lambda x: x.rolling(horizon, min_periods=max(3, horizon//3)).std())
        )
    panel["dollar_volume"] = panel["close"] * panel["volume"]
    panel["relative_volume_20"] = (
        panel.groupby("symbol", sort=False)["volume"]
        .transform(lambda x: x / x.shift(1).rolling(20, min_periods=10).mean())
    )
    panel.replace([np.inf,-np.inf], np.nan, inplace=True)
    return panel
