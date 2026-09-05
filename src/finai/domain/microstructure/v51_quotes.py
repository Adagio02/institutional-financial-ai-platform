from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


QUOTE_COLUMNS = ["timestamp", "symbol", "bid_price", "ask_price", "bid_size", "ask_size"]
SIGNAL_COLUMNS = [
    "alpha__quoted_spread_reversion",
    "alpha__order_book_imbalance",
    "alpha__microprice_pressure",
    "alpha__depth_adjusted_pressure",
]


def normalize_quotes(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    aliases = {
        "bid": "bid_price", "ask": "ask_price", "bp": "bid_price", "ap": "ask_price",
        "bs": "bid_size", "as": "ask_size", "time": "timestamp", "t": "timestamp",
        "ticker": "symbol", "S": "symbol",
    }
    source = frame.rename(columns={key: value for key, value in aliases.items() if key in frame})
    missing = sorted(set(QUOTE_COLUMNS).difference(source.columns))
    if missing:
        raise ValueError("V5.1 quote input missing: " + ", ".join(missing))
    output = source[QUOTE_COLUMNS].copy()
    input_rows = len(output)
    output["timestamp"] = pd.to_datetime(output["timestamp"], utc=True, errors="coerce")
    output["symbol"] = output["symbol"].astype(str).str.upper().str.strip()
    for column in QUOTE_COLUMNS[2:]:
        output[column] = pd.to_numeric(output[column], errors="coerce")
    valid = (
        output["timestamp"].notna() & output["symbol"].ne("")
        & output["bid_price"].gt(0) & output["ask_price"].ge(output["bid_price"])
        & output["bid_size"].gt(0) & output["ask_size"].gt(0)
    )
    output = output.loc[valid].sort_values(["timestamp", "symbol"])
    output = output.drop_duplicates(["timestamp", "symbol"], keep="last").reset_index(drop=True)
    if output.empty:
        raise RuntimeError("V5.1 normalization rejected every quote.")
    return output, {
        "input_rows": int(input_rows),
        "accepted_rows": int(len(output)),
        "rejected_rows": int(input_rows - len(output)),
    }


def _centered_rank(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    ranked = values.groupby(frame["timestamp"]).rank(pct=True, method="average")
    return ranked - ranked.groupby(frame["timestamp"]).transform("mean")


def build_microstructure_signals(quotes: pd.DataFrame) -> pd.DataFrame:
    output = quotes.copy()
    output["midpoint"] = (output["bid_price"] + output["ask_price"]) / 2.0
    output["quoted_spread"] = output["ask_price"] - output["bid_price"]
    output["quoted_spread_bps"] = output["quoted_spread"] / output["midpoint"] * 10_000.0
    depth = output["bid_size"] + output["ask_size"]
    output["book_imbalance"] = (output["bid_size"] - output["ask_size"]) / depth
    output["microprice"] = (
        output["ask_price"] * output["bid_size"]
        + output["bid_price"] * output["ask_size"]
    ) / depth
    output["microprice_deviation_bps"] = (
        (output["microprice"] - output["midpoint"]) / output["midpoint"] * 10_000.0
    )
    output["total_depth"] = depth
    output["alpha__quoted_spread_reversion"] = -_centered_rank(
        output, output["quoted_spread_bps"]
    )
    output["alpha__order_book_imbalance"] = _centered_rank(
        output, output["book_imbalance"]
    )
    output["alpha__microprice_pressure"] = _centered_rank(
        output, output["microprice_deviation_bps"]
    )
    pressure = output["book_imbalance"] * np.log1p(output["total_depth"])
    output["alpha__depth_adjusted_pressure"] = _centered_rank(output, pressure)
    return output


def qualify_microstructure_signals(frame: pd.DataFrame) -> list[dict[str, Any]]:
    ordered = frame.sort_values(["symbol", "timestamp"]).copy()
    ordered["forward_mid_return"] = (
        ordered.groupby("symbol")["midpoint"].shift(-1) / ordered["midpoint"] - 1.0
    )
    results: list[dict[str, Any]] = []
    for column in SIGNAL_COLUMNS:
        daily = ordered.groupby("timestamp", observed=True).apply(
            lambda section: section[column].corr(
                section["forward_mid_return"], method="spearman"
            ),
            include_groups=False,
        ).dropna()
        mean_ic = float(daily.mean()) if len(daily) else 0.0
        std_ic = float(daily.std(ddof=0)) if len(daily) else 0.0
        results.append({
            "signal_column": column,
            "period_count": int(len(daily)),
            "mean_rank_ic": mean_ic,
            "rank_ic_information_ratio": float(mean_ic / std_ic) if std_ic > 0 else 0.0,
            "positive_rank_ic_fraction": float((daily > 0).mean()) if len(daily) else 0.0,
            "eligible_for_v52_research": bool(len(daily) >= 3 and np.isfinite(mean_ic)),
        })
    return sorted(results, key=lambda item: abs(float(item["mean_rank_ic"])), reverse=True)
