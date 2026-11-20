"""Break down the V4.2.1 holdout loss (-22.77% on 2026-10-02).

Run from the project root with the project's virtual environment active:
    python diagnose_v421_holdout.py

It rebuilds the same dataset and research/holdout split as the learning cycle,
refits the winning model on research rows ONLY (the saved .joblib was refit on
all rows, including the holdout, so it cannot be used for an honest holdout
check), then replays the holdout trades and reports where the losses came from.
Nothing is written to the database or to the champion/candidate artifacts.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone

from finai.application.services.v421_learning_factory import create_v41_learning_service
from finai.core.config import get_settings


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="v41_regime_extra_trees")
    p.add_argument("--long-threshold", type=float, default=0.44)
    p.add_argument("--short-threshold", type=float, default=0.40)
    p.add_argument("--rows", type=int, default=110_647,
                   help="rows_used from the 2026-10-02 run, so later bars are excluded")
    return p.parse_args()


def describe(label: str, trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {"group": label, "trades": 0}
    gross = trades.gross_return
    return {
        "group": label,
        "trades": len(trades),
        "mean_gross_bps": gross.mean() * 1e4,
        "mean_net_bps": trades.net_return.mean() * 1e4,
        "hit_rate": (gross > 0).mean(),
        "compounded_net": (1 + trades.net_return).prod() - 1,
    }


def main() -> None:
    args = parse_args()
    settings = get_settings()
    service = create_v41_learning_service(settings=settings)
    horizon = int(settings.v41_forward_horizon_bars)
    cost = settings.v41_round_trip_cost_bps / 1e4

    dataset, _ = service.build_dataset(
        symbol=settings.v41_learning_symbol,
        interval=settings.v41_learning_interval,
        include_target=True,
    )
    print(f"Rows available now: {len(dataset):,}; using first {min(args.rows, len(dataset)):,}")
    dataset = dataset.iloc[: args.rows].reset_index(drop=True)

    # Same split as V41LearningService.run_learning_cycle
    holdout_rows = max(1, int(len(dataset) * settings.v41_holdout_fraction))
    research_end = len(dataset) - holdout_rows - settings.v41_purge_rows
    research = dataset.iloc[:research_end]
    holdout = dataset.iloc[-holdout_rows:].reset_index(drop=True)
    holdout_offset = len(dataset) - holdout_rows

    features = list(service.feature_columns)
    model = clone(service.create_model_templates()[args.model])
    model.fit(research[features], research["target"])

    positions = service.positions_from_probabilities(
        probabilities=model.predict_proba(holdout[features]),
        classes=model.classes_,
        long_threshold=args.long_threshold,
        short_threshold=args.short_threshold,
    )

    timestamps = pd.to_datetime(dataset["timestamp"], utc=True).dt.tz_convert("America/New_York")
    records, i = [], 0
    while i < len(holdout):  # same non-overlapping walk as V4.2.1 simulate()
        side, fwd = int(positions[i]), float(holdout.forward_return.iloc[i])
        if side == 0 or not np.isfinite(fwd):
            i += 1
            continue
        entry_pos = holdout_offset + i
        exit_pos = min(entry_pos + horizon, len(dataset) - 1)
        entry, exit_ = timestamps.iloc[entry_pos], timestamps.iloc[exit_pos]
        records.append({
            "entry_time_et": entry,
            "side": "long" if side > 0 else "short",
            "gross_return": side * fwd,
            "net_return": side * fwd - cost,
            "elapsed_minutes": (exit_ - entry).total_seconds() / 60,
            "crosses_overnight": exit_.date() != entry.date(),
            "minutes_from_open": float(holdout.minutes_from_open.iloc[i]),
        })
        i += horizon
    trades = pd.DataFrame(records)

    total = (1 + trades.net_return).prod() - 1
    print(f"\nReplayed holdout: {len(trades)} trades, compounded net {total:.2%} "
          f"(original run: -22.77% on 271 trades; small differences are expected)")

    hold_ts = timestamps.iloc[holdout_offset:]
    drift = holdout.forward_return.mean() * 1e4
    print(f"Holdout period: {hold_ts.iloc[0]:%Y-%m-%d} to {hold_ts.iloc[-1]:%Y-%m-%d}")
    print(f"Average {horizon}-bar AAPL move over all holdout rows: {drift:+.2f} bps "
          f"(the drift a long-only or short-only bias would capture)")

    trades["month"] = trades.entry_time_et.dt.strftime("%Y-%m")
    trades["session"] = pd.cut(
        trades.minutes_from_open, [-np.inf, -0.5, 60, 330, 390, np.inf],
        labels=["pre-market", "first hour", "midday", "last hour", "after-hours"],
    )
    groups = [describe("ALL", trades)]
    groups += [describe(f"side={k}", g) for k, g in trades.groupby("side")]
    groups += [describe(f"overnight={k}", g) for k, g in trades.groupby("crosses_overnight")]
    groups += [describe(f"session={k}", g) for k, g in trades.groupby("session", observed=True)]
    groups += [describe(f"month={k}", g) for k, g in trades.groupby("month")]
    table = pd.DataFrame(groups)
    with pd.option_context("display.float_format", "{:,.3f}".format, "display.width", 140):
        print("\n" + table.to_string(index=False))

    stretched = (trades.elapsed_minutes > horizon * 1.5).mean()
    print(f"\nTrades whose {horizon}-bar window spanned more than {horizon * 1.5:.0f} minutes: "
          f"{stretched:.1%} (missing bars or overnight gaps stretch the holding period)")

    out = Path("artifacts/v41/holdout_trade_diagnostics.csv")
    trades.to_csv(out, index=False)
    print(f"Trade-by-trade detail written to {out}")


if __name__ == "__main__":
    main()
