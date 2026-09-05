from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


KEYS = ["timestamp", "symbol"]


def normalize_signal_family(frame: pd.DataFrame, family: str) -> pd.DataFrame:
    source = frame.rename(columns={"underlying_symbol": "symbol"}).copy()
    missing = sorted(set(KEYS).difference(source.columns))
    if missing:
        raise ValueError(f"V5.4 {family} panel missing: " + ", ".join(missing))
    alpha = [column for column in source.columns if column.startswith("alpha__")]
    if not alpha:
        raise ValueError(f"V5.4 {family} panel contains no alpha__ columns.")
    source["timestamp"] = pd.to_datetime(source["timestamp"], utc=True, errors="coerce").dt.floor("D")
    source["symbol"] = source["symbol"].astype(str).str.upper().str.strip()
    for column in alpha:
        source[column] = pd.to_numeric(source[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
    renamed = {column: f"alpha__{family}__{column.removeprefix('alpha__')}" for column in alpha}
    output = source[KEYS + alpha].rename(columns=renamed).dropna(subset=KEYS)
    return output.groupby(KEYS, as_index=False, observed=True).mean(numeric_only=True)


def align_signal_families(families: dict[str, pd.DataFrame], target: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    if len(families) < 2:
        raise ValueError("V5.4 requires at least two independent alpha families.")
    target_source = target.rename(columns={"underlying_symbol": "symbol", "underlying_price": "close"}).copy()
    if not {"timestamp", "symbol", "close"}.issubset(target_source.columns):
        raise ValueError("V5.4 target panel requires timestamp, symbol, and close.")
    target_source["timestamp"] = pd.to_datetime(target_source["timestamp"], utc=True, errors="coerce").dt.floor("D")
    target_source["symbol"] = target_source["symbol"].astype(str).str.upper().str.strip()
    target_source["close"] = pd.to_numeric(target_source["close"], errors="coerce")
    panel = target_source[KEYS + ["close"]].dropna().groupby(KEYS, as_index=False).last()
    diagnostics: dict[str, Any] = {"target_rows": int(len(panel)), "families": {}}
    for name, frame in families.items():
        normalized = normalize_signal_family(frame, name)
        diagnostics["families"][name] = {
            "rows": int(len(normalized)),
            "signals": int(sum(column.startswith("alpha__") for column in normalized.columns)),
        }
        panel = panel.merge(normalized, on=KEYS, how="left", validate="one_to_one")
    alpha = [column for column in panel if column.startswith("alpha__")]
    panel[alpha] = panel.groupby("timestamp")[alpha].transform(
        lambda values: values.fillna(values.median()).fillna(0.0)
    )
    active = panel[alpha].abs().sum(axis=1).gt(0)
    panel = panel.loc[active].sort_values(KEYS).reset_index(drop=True)
    diagnostics.update({
        "aligned_rows": int(len(panel)), "periods": int(panel["timestamp"].nunique()),
        "symbols": int(panel["symbol"].nunique()), "signal_columns": alpha,
    })
    if panel.empty:
        raise RuntimeError("V5.4 found no usable aligned observations.")
    return panel, diagnostics


def _cross_sectional_rank(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    ranked = frame.copy()
    for column in columns:
        values = ranked.groupby("timestamp")[column].rank(pct=True, method="average")
        ranked[column] = values - values.groupby(ranked["timestamp"]).transform("mean")
    return ranked


def build_expanding_ensemble(panel: pd.DataFrame, minimum_training_periods: int = 3) -> tuple[pd.DataFrame, pd.DataFrame]:
    alpha = [column for column in panel if column.startswith("alpha__")]
    ranked = _cross_sectional_rank(panel, alpha).sort_values(KEYS).copy()
    ranked["forward_return"] = ranked.groupby("symbol")["close"].shift(-1) / ranked["close"] - 1.0
    dates = list(ranked["timestamp"].drop_duplicates().sort_values())
    output_parts, weight_rows = [], []
    equal = np.repeat(1.0 / len(alpha), len(alpha))
    for index, date in enumerate(dates):
        current = ranked.loc[ranked["timestamp"] == date].copy()
        training_dates = dates[: max(0, index - 1)]
        training = ranked.loc[ranked["timestamp"].isin(training_dates)].dropna(subset=["forward_return"])
        scores = []
        for column in alpha:
            daily = training.groupby("timestamp", observed=True).apply(
                lambda section: section[column].corr(section["forward_return"], method="spearman"),
                include_groups=False,
            ).dropna()
            scores.append(float(daily.mean()) if len(daily) >= minimum_training_periods else 0.0)
        scores_array = np.asarray(scores, dtype=float)
        weights = equal if np.abs(scores_array).sum() <= 1e-12 else scores_array / np.abs(scores_array).sum()
        current["alpha__ensemble"] = current[alpha].to_numpy() @ weights
        current["ensemble_training_periods"] = len(training_dates)
        output_parts.append(current)
        weight_rows.append({"timestamp": date, **{column: float(weight) for column, weight in zip(alpha, weights)}})
    ensemble = pd.concat(output_parts, ignore_index=True)
    return ensemble[KEYS + ["close", "forward_return", "alpha__ensemble", "ensemble_training_periods"]], pd.DataFrame(weight_rows)


def qualify_ensemble(ensemble: pd.DataFrame, weights: pd.DataFrame, minimum_periods: int = 3) -> dict[str, Any]:
    daily_ic = ensemble.groupby("timestamp", observed=True).apply(
        lambda section: section["alpha__ensemble"].corr(section["forward_return"], method="spearman"),
        include_groups=False,
    ).dropna()
    positions = ensemble.pivot(index="timestamp", columns="symbol", values="alpha__ensemble").sort_index()
    turnover = positions.diff().abs().sum(axis=1).dropna()
    weight_columns = [column for column in weights if column.startswith("alpha__")]
    weight_turnover = weights[weight_columns].diff().abs().sum(axis=1).dropna()
    mean_ic = float(daily_ic.mean()) if len(daily_ic) else 0.0
    std_ic = float(daily_ic.std(ddof=0)) if len(daily_ic) else 0.0
    return {
        "period_count": int(len(daily_ic)), "mean_rank_ic": mean_ic,
        "rank_ic_information_ratio": float(mean_ic / std_ic) if std_ic > 0 else 0.0,
        "positive_rank_ic_fraction": float((daily_ic > 0).mean()) if len(daily_ic) else 0.0,
        "mean_signal_turnover": float(turnover.mean()) if len(turnover) else 0.0,
        "mean_weight_turnover": float(weight_turnover.mean()) if len(weight_turnover) else 0.0,
        "eligible_for_v55_walk_forward": bool(len(daily_ic) >= minimum_periods and np.isfinite(mean_ic)),
    }

