"""Per-feature information coefficient (IC) report for the V5.6 research panel.

Run from the project root with the virtual environment active:
    python feature_ic_report.py --input .\\data\\research\\v56-research-005-enriched\\model_panel.parquet

For every numeric feature it measures, on non-overlapping rebalance dates, the
cross-sectional Spearman rank correlation with future returns:
  - raw IC:      against the plain forward return
  - residual IC: against the forward return after removing sector and beta
                 (the target V008 trains on), when sector and beta columns exist
It reports the mean IC, its t-statistic, hit rate, year-by-year stability,
coverage, and how the IC decays across horizons. Nothing is trained; the panel
is only read. Results go to artifacts/v56-feature-ic/.

Reading the output:
  - Typical useful equity signals have |mean IC| of roughly 0.01-0.05.
  - With dozens of features tested, require |t| >= 3 (not 2) before believing one.
  - A feature only counts if its IC keeps the same sign in most years.
  - Every feature here was already seen during V5.6 research, so a strong result
    is a hypothesis to confirm on new data, not a finished signal.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from finai.research.v56.core import Config, numeric_features, read_frame

KEYS = ["timestamp", "symbol"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", required=True, help="model panel (parquet/csv/pkl.gz)")
    p.add_argument("--output", default="artifacts/v56-feature-ic")
    p.add_argument("--horizon", type=int, default=5, help="main forward horizon in periods")
    p.add_argument("--decay-horizons", type=int, nargs="*", default=[1, 5, 21, 63])
    p.add_argument("--min-symbols", type=int, default=30, help="minimum names per date to score it")
    p.add_argument("--t-threshold", type=float, default=3.0)
    return p.parse_args()


def forward_returns(frame: pd.DataFrame, horizon: int) -> pd.Series:
    return frame.groupby("symbol", observed=True)["close"].transform(lambda s: s.shift(-horizon) / s - 1.0)


def residualize(frame: pd.DataFrame, column: str) -> pd.Series:
    """Per date: residual of `column` on sector dummies and beta (same idea as V008)."""
    out = pd.Series(np.nan, index=frame.index, dtype=float)
    valid = frame[column].notna() & frame["beta"].notna() & frame["sector"].notna()
    for _, section in frame.loc[valid].groupby("timestamp", observed=True):
        if len(section) < 10:
            continue
        dummies = pd.get_dummies(section["sector"], dtype=float).to_numpy()
        design = np.column_stack([dummies, section["beta"].to_numpy(float)])
        y = section[column].to_numpy(float)
        coef = np.linalg.lstsq(design, y, rcond=None)[0]
        out.loc[section.index] = y - design @ coef
    return out


def daily_rank_ic(frame: pd.DataFrame, feature: str, target: str, min_symbols: int) -> pd.Series:
    """Spearman IC per date, vectorized: rank within date, then Pearson of the ranks."""
    sub = frame[["timestamp", feature, target]].dropna()
    counts = sub.groupby("timestamp", observed=True)[feature].transform("size")
    sub = sub.loc[counts >= min_symbols]
    if sub.empty:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC"))
    ranks = sub.groupby("timestamp", observed=True)[[feature, target]].rank()
    ranks["timestamp"] = sub["timestamp"]
    demeaned = ranks[[feature, target]] - ranks.groupby("timestamp", observed=True)[[feature, target]].transform("mean")
    demeaned["timestamp"] = sub["timestamp"]
    demeaned["xy"] = demeaned[feature] * demeaned[target]
    demeaned["xx"] = demeaned[feature] ** 2
    demeaned["yy"] = demeaned[target] ** 2
    sums = demeaned.groupby("timestamp", observed=True)[["xy", "xx", "yy"]].sum()
    denom = np.sqrt(sums.xx * sums.yy)
    return (sums.xy / denom.replace(0, np.nan)).dropna()


def summarize(ic: pd.Series, horizon: int) -> dict:
    n = len(ic)
    if n < 3:
        return {"dates": n}
    mean, std = ic.mean(), ic.std(ddof=1)
    yearly = ic.groupby(ic.index.year).mean()
    sign = np.sign(mean)
    return {
        "dates": n,
        "mean_ic": mean,
        "t_stat": mean / std * np.sqrt(n) if std > 0 else 0.0,
        "annual_icir": mean / std * np.sqrt(252 / horizon) if std > 0 else 0.0,
        "hit_rate": (np.sign(ic) == sign).mean() if sign != 0 else 0.5,
        "years": len(yearly),
        "same_sign_years": (np.sign(yearly) == sign).mean() if sign != 0 else 0.0,
    }


def main() -> None:
    args = parse_args()
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    frame = read_frame(args.input)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["symbol"] = frame["symbol"].astype(str).str.upper().str.strip()
    frame = frame.sort_values(KEYS).drop_duplicates(KEYS, keep="last").reset_index(drop=True)

    horizons = sorted(set(args.decay_horizons) | {args.horizon})
    for h in horizons:
        frame[f"fwd_{h}"] = forward_returns(frame, h)
    features = numeric_features(frame.drop(columns=[f"fwd_{h}" for h in horizons]))

    # Non-overlapping scoring dates: every `horizon`-th date.
    dates = np.array(sorted(frame["timestamp"].unique()))
    has_residual = {"sector", "beta"}.issubset(frame.columns)
    main_target = f"fwd_{args.horizon}"
    if has_residual:
        print("Residualizing the main target by sector and beta...")
        scored = frame.timestamp.isin(dates[:: args.horizon])
        frame["resid_target"] = residualize(frame.loc[scored], main_target).reindex(frame.index)
    names_per_date = frame.groupby("timestamp")["symbol"].nunique()
    print(f"Panel: {len(frame):,} rows, {frame.symbol.nunique()} symbols, {len(dates)} dates "
          f"({pd.Timestamp(dates[0]):%Y-%m-%d} to {pd.Timestamp(dates[-1]):%Y-%m-%d}); "
          f"median {names_per_date.median():.0f} names per date")
    rows, yearly_rows = [], []
    for feature in features:
        coverage = frame[feature].notna().mean()
        row = {"feature": feature, "coverage": coverage}
        for h in horizons:
            sampled = frame[frame.timestamp.isin(dates[:: max(1, h)])]
            ic = daily_rank_ic(sampled, feature, f"fwd_{h}", args.min_symbols)
            if h == args.horizon:
                stats = summarize(ic, h)
                row.update({f"raw_{k}": v for k, v in stats.items()})
                for year, value in ic.groupby(ic.index.year).mean().items():
                    yearly_rows.append({"feature": feature, "target": "raw", "year": year, "mean_ic": value})
            else:
                row[f"raw_mean_ic_h{h}"] = ic.mean() if len(ic) else np.nan
        if has_residual:
            sampled = frame[frame.timestamp.isin(dates[:: args.horizon])]
            ic = daily_rank_ic(sampled, feature, "resid_target", args.min_symbols)
            row.update({f"resid_{k}": v for k, v in summarize(ic, args.horizon).items()})
            for year, value in ic.groupby(ic.index.year).mean().items():
                yearly_rows.append({"feature": feature, "target": "residual", "year": year, "mean_ic": value})
        rows.append(row)

    table = pd.DataFrame(rows)
    key = "resid" if has_residual else "raw"
    table["passes"] = (
        (table.get(f"{key}_t_stat", 0).abs() >= args.t_threshold)
        & (table.get(f"{key}_same_sign_years", 0) >= 0.75)
        & (table.coverage >= 0.60)
    )
    table = table.sort_values(f"{key}_t_stat", key=lambda s: s.abs(), ascending=False)
    table.to_csv(out_dir / "feature_ic_summary.csv", index=False)
    yearly = pd.DataFrame(yearly_rows)
    if not yearly.empty:
        yearly.pivot_table(index=["feature", "target"], columns="year", values="mean_ic").to_csv(
            out_dir / "feature_ic_by_year.csv")

    show = ["feature", "coverage", f"{key}_mean_ic", f"{key}_t_stat", f"{key}_hit_rate",
            f"{key}_same_sign_years", "raw_mean_ic"] + [f"raw_mean_ic_h{h}" for h in horizons if h != args.horizon]
    show = [c for c in dict.fromkeys(show) if c in table.columns] + ["passes"]
    target_name = "residual (sector/beta-neutral)" if has_residual else "raw"
    print(f"\nRank IC vs {args.horizon}-period {target_name} forward return, sorted by |t|. "
          f"Pass = |t| >= {args.t_threshold}, same sign in >= 75% of years, coverage >= 60%.")
    with pd.option_context("display.float_format", "{:,.4f}".format, "display.width", 200,
                           "display.max_rows", 200):
        print(table[show].to_string(index=False))
    passed = table.loc[table.passes, "feature"].tolist()
    print(f"\n{len(passed)} of {len(table)} features pass: {passed if passed else 'none'}")
    print(f"Written: {out_dir / 'feature_ic_summary.csv'} and {out_dir / 'feature_ic_by_year.csv'}")


if __name__ == "__main__":
    main()

