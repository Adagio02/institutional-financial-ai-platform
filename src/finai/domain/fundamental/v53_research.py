from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np
import pandas as pd


SIGNAL_COLUMNS = [
    "alpha__fundamental_value",
    "alpha__fundamental_quality",
    "alpha__fundamental_growth",
    "alpha__event_surprise",
    "alpha__news_sentiment",
    "alpha__fundamental_event_news",
]


def _require(frame: pd.DataFrame, columns: set[str], label: str) -> None:
    missing = sorted(columns.difference(frame.columns))
    if missing:
        raise ValueError(f"V5.3 {label} input missing: " + ", ".join(missing))


def _utc(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, utc=True, errors="coerce")


def _number(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan)


def normalize_fundamentals(frame: pd.DataFrame) -> pd.DataFrame:
    aliases = {"ticker": "symbol", "filed_at": "available_at", "filing_date": "available_at"}
    source = frame.rename(columns={k: v for k, v in aliases.items() if k in frame.columns}).copy()
    required = {
        "symbol", "available_at", "period_end", "revenue", "net_income",
        "operating_cash_flow", "total_assets", "total_equity", "market_cap",
    }
    _require(source, required, "fundamental")
    output = source[list(sorted(required))].copy()
    output["symbol"] = output["symbol"].astype(str).str.upper().str.strip()
    output["available_at"] = _utc(output["available_at"])
    output["period_end"] = _utc(output["period_end"])
    for column in required - {"symbol", "available_at", "period_end"}:
        output[column] = _number(output[column])
    output = output.loc[
        output["symbol"].ne("") & output["available_at"].notna()
        & output["period_end"].notna() & output["period_end"].le(output["available_at"])
        & output["total_assets"].gt(0) & output["market_cap"].gt(0)
    ]
    output = output.drop_duplicates(["symbol", "period_end", "available_at"], keep="last")
    if output.empty:
        raise RuntimeError("V5.3 rejected every fundamental observation.")
    return output.sort_values(["available_at", "symbol"]).reset_index(drop=True)


def normalize_events(frame: pd.DataFrame) -> pd.DataFrame:
    aliases = {"ticker": "symbol", "timestamp": "available_at", "event_time": "available_at"}
    source = frame.rename(columns={k: v for k, v in aliases.items() if k in frame.columns}).copy()
    required = {"symbol", "available_at", "event_type", "actual", "consensus"}
    _require(source, required, "event")
    output = source[list(sorted(required))].copy()
    output["symbol"] = output["symbol"].astype(str).str.upper().str.strip()
    output["available_at"] = _utc(output["available_at"])
    output["event_type"] = output["event_type"].astype(str).str.lower().str.strip()
    output["actual"] = _number(output["actual"])
    output["consensus"] = _number(output["consensus"])
    output = output.dropna(subset=["available_at", "actual", "consensus"])
    output = output.loc[output["symbol"].ne("")]
    output["event_surprise"] = (
        (output["actual"] - output["consensus"])
        / output["consensus"].abs().clip(lower=1e-9)
    ).clip(-5.0, 5.0)
    return output.sort_values(["available_at", "symbol"]).reset_index(drop=True)


def normalize_news(frame: pd.DataFrame) -> pd.DataFrame:
    aliases = {"ticker": "symbol", "timestamp": "published_at", "time": "published_at"}
    source = frame.rename(columns={k: v for k, v in aliases.items() if k in frame.columns}).copy()
    required = {"symbol", "published_at", "headline", "sentiment"}
    _require(source, required, "news")
    output = source[list(sorted(required))].copy()
    output["symbol"] = output["symbol"].astype(str).str.upper().str.strip()
    output["published_at"] = _utc(output["published_at"])
    output["headline"] = output["headline"].fillna("").astype(str).str.strip()
    output["sentiment"] = _number(output["sentiment"]).clip(-1.0, 1.0)
    output = output.dropna(subset=["published_at", "sentiment"])
    output = output.loc[output["symbol"].ne("") & output["headline"].ne("")]
    output["headline_id"] = output["headline"].map(
        lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]
    )
    return output.drop_duplicates(["symbol", "published_at", "headline_id"]).sort_values(
        ["published_at", "symbol"]
    ).reset_index(drop=True)


def normalize_prices(frame: pd.DataFrame) -> pd.DataFrame:
    aliases = {"ticker": "symbol", "date": "timestamp", "adj_close": "close"}
    source = frame.rename(columns={k: v for k, v in aliases.items() if k in frame.columns}).copy()
    _require(source, {"timestamp", "symbol", "close"}, "price")
    output = source[["timestamp", "symbol", "close"]].copy()
    output["timestamp"] = _utc(output["timestamp"])
    output["symbol"] = output["symbol"].astype(str).str.upper().str.strip()
    output["close"] = _number(output["close"])
    output = output.dropna().loc[lambda value: value["close"].gt(0)]
    output = output.drop_duplicates(["timestamp", "symbol"], keep="last")
    return output.sort_values(["timestamp", "symbol"]).reset_index(drop=True)


def build_point_in_time_features(
    fundamentals: pd.DataFrame,
    events: pd.DataFrame,
    news: pd.DataFrame,
    prices: pd.DataFrame,
) -> pd.DataFrame:
    base = prices.sort_values(["timestamp", "symbol"]).copy()
    rows: list[pd.DataFrame] = []
    for symbol, section in base.groupby("symbol", observed=True):
        section = section.sort_values("timestamp")
        f = fundamentals.loc[fundamentals["symbol"] == symbol].sort_values("available_at")
        if f.empty:
            continue
        joined = pd.merge_asof(
            section, f.drop(columns="symbol"), left_on="timestamp", right_on="available_at",
            direction="backward", allow_exact_matches=True,
        )
        joined["symbol"] = symbol
        event = events.loc[events["symbol"] == symbol].sort_values("available_at")
        if not event.empty:
            event_daily = event.set_index("available_at")["event_surprise"].rolling("7D").mean()
            event_daily = event_daily[~event_daily.index.duplicated(keep="last")].reset_index()
            joined = pd.merge_asof(
                joined.sort_values("timestamp"), event_daily, left_on="timestamp",
                right_on="available_at", direction="backward", tolerance=pd.Timedelta("7D"),
                suffixes=("", "_event"),
            )
        else:
            joined["event_surprise"] = 0.0
        story = news.loc[news["symbol"] == symbol].sort_values("published_at")
        if not story.empty:
            news_daily = story.set_index("published_at")["sentiment"].rolling("3D").mean()
            news_daily = news_daily[~news_daily.index.duplicated(keep="last")].reset_index()
            joined = pd.merge_asof(
                joined.sort_values("timestamp"), news_daily, left_on="timestamp",
                right_on="published_at", direction="backward", tolerance=pd.Timedelta("3D"),
            )
        else:
            joined["sentiment"] = 0.0
        rows.append(joined)
    if not rows:
        raise RuntimeError("V5.3 has no symbol overlap between prices and fundamentals.")
    output = pd.concat(rows, ignore_index=True).sort_values(["timestamp", "symbol"])
    output["earnings_yield"] = output["net_income"] / output["market_cap"]
    output["cash_flow_yield"] = output["operating_cash_flow"] / output["market_cap"]
    output["return_on_assets"] = output["net_income"] / output["total_assets"]
    output["cash_conversion"] = output["operating_cash_flow"] / output["net_income"].abs().clip(1e-9)
    output["revenue_growth"] = output.groupby("symbol")["revenue"].pct_change(fill_method=None)
    output["event_surprise"] = output["event_surprise"].fillna(0.0)
    output["sentiment"] = output["sentiment"].fillna(0.0)
    output["source_available_at"] = output["available_at"]
    if (output["source_available_at"] > output["timestamp"]).any():
        raise RuntimeError("V5.3 point-in-time join introduced look-ahead data.")
    keep = [
        "timestamp", "symbol", "close", "source_available_at", "period_end",
        "earnings_yield", "cash_flow_yield", "return_on_assets", "cash_conversion",
        "revenue_growth", "event_surprise", "sentiment",
    ]
    return output[keep].replace([np.inf, -np.inf], np.nan).reset_index(drop=True)


def _rank(frame: pd.DataFrame, column: str) -> pd.Series:
    values = frame.groupby("timestamp")[column].transform(
        lambda part: part.fillna(part.median()).fillna(0.0)
    )
    ranked = values.groupby(frame["timestamp"]).rank(pct=True, method="average")
    return ranked - ranked.groupby(frame["timestamp"]).transform("mean")


def build_signals(features: pd.DataFrame) -> pd.DataFrame:
    output = features[["timestamp", "symbol", "close", "source_available_at"]].copy()
    output["alpha__fundamental_value"] = 0.5 * _rank(features, "earnings_yield") + 0.5 * _rank(features, "cash_flow_yield")
    output["alpha__fundamental_quality"] = 0.5 * _rank(features, "return_on_assets") + 0.5 * _rank(features, "cash_conversion")
    output["alpha__fundamental_growth"] = _rank(features, "revenue_growth")
    output["alpha__event_surprise"] = _rank(features, "event_surprise")
    output["alpha__news_sentiment"] = _rank(features, "sentiment")
    output["alpha__fundamental_event_news"] = (
        0.25 * output["alpha__fundamental_value"]
        + 0.20 * output["alpha__fundamental_quality"]
        + 0.15 * output["alpha__fundamental_growth"]
        + 0.20 * output["alpha__event_surprise"]
        + 0.20 * output["alpha__news_sentiment"]
    )
    return output.sort_values(["timestamp", "symbol"]).reset_index(drop=True)


def qualify_signals(signals: pd.DataFrame, *, minimum_periods: int = 3) -> list[dict[str, Any]]:
    ordered = signals.sort_values(["symbol", "timestamp"]).copy()
    ordered["forward_return"] = ordered.groupby("symbol")["close"].shift(-1) / ordered["close"] - 1.0
    results: list[dict[str, Any]] = []
    for column in SIGNAL_COLUMNS:
        daily = ordered.groupby("timestamp", observed=True).apply(
            lambda part: part[column].corr(part["forward_return"], method="spearman"),
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
            "eligible_for_v54_ensemble_research": bool(len(daily) >= minimum_periods and np.isfinite(mean_ic)),
        })
    return sorted(results, key=lambda item: abs(float(item["mean_rank_ic"])), reverse=True)


def dataset_manifest(frames: dict[str, pd.DataFrame], provenance: str) -> dict[str, Any]:
    payload = {
        "schema_version": "1.0",
        "stage": "v5.3",
        "provenance": provenance,
        "synthetic": provenance.lower() in {"synthetic", "demo", "test"},
        "datasets": {name: {"rows": int(len(frame)), "columns": list(frame.columns)} for name, frame in frames.items()},
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return payload

