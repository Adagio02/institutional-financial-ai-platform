from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


OPTION_COLUMNS = [
    "timestamp", "underlying_symbol", "expiration", "strike", "option_type",
    "bid_price", "ask_price", "implied_volatility", "delta", "gamma",
    "open_interest", "volume", "underlying_price",
]
SIGNAL_COLUMNS = [
    "alpha__atm_iv_reversion", "alpha__put_call_skew", "alpha__term_structure",
    "alpha__put_call_activity", "alpha__gamma_pressure",
]


def normalize_option_chain(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    aliases = {
        "symbol": "underlying_symbol", "root_symbol": "underlying_symbol",
        "expiry": "expiration", "expiration_date": "expiration", "type": "option_type",
        "right": "option_type", "bid": "bid_price", "ask": "ask_price",
        "iv": "implied_volatility", "oi": "open_interest",
        "underlying": "underlying_price", "spot": "underlying_price",
    }
    source = frame.rename(columns={key: value for key, value in aliases.items() if key in frame})
    missing = sorted(set(OPTION_COLUMNS).difference(source.columns))
    if missing:
        raise ValueError("V5.2 option-chain input missing: " + ", ".join(missing))
    output = source[OPTION_COLUMNS].copy()
    input_rows = len(output)
    output["timestamp"] = pd.to_datetime(output["timestamp"], utc=True, errors="coerce")
    output["expiration"] = pd.to_datetime(output["expiration"], utc=True, errors="coerce")
    output["underlying_symbol"] = output["underlying_symbol"].astype(str).str.upper().str.strip()
    option_type = output["option_type"].astype(str).str.upper().str.strip()
    output["option_type"] = option_type.replace({"CALL": "C", "PUT": "P"})
    numeric = [column for column in OPTION_COLUMNS if column not in {
        "timestamp", "expiration", "underlying_symbol", "option_type"
    }]
    for column in numeric:
        output[column] = pd.to_numeric(output[column], errors="coerce")
    valid = (
        output["timestamp"].notna() & output["expiration"].gt(output["timestamp"])
        & output["underlying_symbol"].ne("") & output["option_type"].isin(["C", "P"])
        & output["strike"].gt(0) & output["underlying_price"].gt(0)
        & output["bid_price"].ge(0) & output["ask_price"].ge(output["bid_price"])
        & output["implied_volatility"].gt(0) & output["implied_volatility"].lt(10)
        & output["open_interest"].ge(0) & output["volume"].ge(0)
    )
    output = output.loc[valid].copy()
    output["timestamp"] = output["timestamp"].dt.floor("min")
    output["days_to_expiration"] = (
        output["expiration"] - output["timestamp"]
    ).dt.total_seconds() / 86_400.0
    output["moneyness"] = output["strike"] / output["underlying_price"] - 1.0
    output = output.drop_duplicates(
        ["timestamp", "underlying_symbol", "expiration", "strike", "option_type"],
        keep="last",
    ).sort_values(["timestamp", "underlying_symbol", "expiration", "strike"])
    if output.empty:
        raise RuntimeError("V5.2 normalization rejected every option observation.")
    return output.reset_index(drop=True), {
        "input_rows": int(input_rows), "accepted_rows": int(len(output)),
        "rejected_rows": int(input_rows - len(output)),
    }


def _weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    valid = values.notna() & weights.notna() & weights.ge(0)
    values = values[valid].astype(float)
    weights = weights[valid].astype(float)
    if not len(values):
        return float("nan")
    if float(weights.sum()) <= 0:
        return float(values.mean())
    return float(np.average(values, weights=weights))


def build_volatility_surface(chain: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    keys = ["timestamp", "underlying_symbol"]
    for (timestamp, symbol), section in chain.groupby(keys, sort=True, observed=True):
        section = section.copy()
        near_expiry = section["days_to_expiration"].min()
        far_expiry = section["days_to_expiration"].max()
        atm = section.loc[section["moneyness"].abs() <= 0.05]
        puts = section.loc[
            (section["option_type"] == "P") & (section["delta"].between(-0.40, -0.10))
        ]
        calls = section.loc[
            (section["option_type"] == "C") & (section["delta"].between(0.10, 0.40))
        ]
        near = section.loc[section["days_to_expiration"] == near_expiry]
        far = section.loc[section["days_to_expiration"] == far_expiry]
        call_volume = float(section.loc[section["option_type"] == "C", "volume"].sum())
        put_volume = float(section.loc[section["option_type"] == "P", "volume"].sum())
        gamma_oi = (section["gamma"].abs() * section["open_interest"]).sum()
        rows.append({
            "timestamp": timestamp, "symbol": symbol,
            "underlying_price": float(section["underlying_price"].median()),
            "atm_implied_volatility": _weighted_mean(
                atm["implied_volatility"], atm["open_interest"]
            ),
            "put_call_iv_skew": _weighted_mean(puts["implied_volatility"], puts["open_interest"])
            - _weighted_mean(calls["implied_volatility"], calls["open_interest"]),
            "iv_term_slope": _weighted_mean(far["implied_volatility"], far["open_interest"])
            - _weighted_mean(near["implied_volatility"], near["open_interest"]),
            "put_call_volume_ratio": put_volume / max(call_volume, 1.0),
            "gamma_open_interest": float(gamma_oi),
            "contract_count": int(len(section)),
        })
    surface = pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan)
    feature_columns = [
        "atm_implied_volatility", "put_call_iv_skew", "iv_term_slope",
        "put_call_volume_ratio", "gamma_open_interest",
    ]
    surface[feature_columns] = surface.groupby("timestamp")[feature_columns].transform(
        lambda values: values.fillna(values.median()).fillna(0.0)
    )
    return surface


def _rank(frame: pd.DataFrame, column: str) -> pd.Series:
    ranked = frame.groupby("timestamp")[column].rank(pct=True, method="average")
    return ranked - ranked.groupby(frame["timestamp"]).transform("mean")


def build_options_signals(surface: pd.DataFrame) -> pd.DataFrame:
    output = surface.copy()
    output["alpha__atm_iv_reversion"] = -_rank(output, "atm_implied_volatility")
    output["alpha__put_call_skew"] = _rank(output, "put_call_iv_skew")
    output["alpha__term_structure"] = -_rank(output, "iv_term_slope")
    output["alpha__put_call_activity"] = -_rank(output, "put_call_volume_ratio")
    output["alpha__gamma_pressure"] = -_rank(output, "gamma_open_interest")
    return output


def qualify_options_signals(frame: pd.DataFrame) -> list[dict[str, Any]]:
    ordered = frame.sort_values(["symbol", "timestamp"]).copy()
    ordered["forward_return"] = (
        ordered.groupby("symbol")["underlying_price"].shift(-1)
        / ordered["underlying_price"] - 1.0
    )
    results = []
    for column in SIGNAL_COLUMNS:
        daily = ordered.groupby("timestamp", observed=True).apply(
            lambda part: part[column].corr(part["forward_return"], method="spearman"),
            include_groups=False,
        ).dropna()
        mean_ic = float(daily.mean()) if len(daily) else 0.0
        standard_deviation = float(daily.std(ddof=0)) if len(daily) else 0.0
        results.append({
            "signal_column": column, "period_count": int(len(daily)),
            "mean_rank_ic": mean_ic,
            "rank_ic_information_ratio": (
                float(mean_ic / standard_deviation) if standard_deviation > 0 else 0.0
            ),
            "positive_rank_ic_fraction": float((daily > 0).mean()) if len(daily) else 0.0,
            "eligible_for_v53_research": bool(len(daily) >= 3 and np.isfinite(mean_ic)),
        })
    return sorted(results, key=lambda item: abs(float(item["mean_rank_ic"])), reverse=True)
