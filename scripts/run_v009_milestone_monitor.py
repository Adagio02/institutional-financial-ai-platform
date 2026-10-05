from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from finai.research.v56.v009_milestones import (
    completed_rebalance_periods,
    qualified_dates,
    read_json,
    seal,
    sha256,
    status_for,
    write_json_atomic,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--panel", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    protocol_path, policy_path, panel_path = map(Path, (args.protocol, args.policy, args.panel))
    protocol, policy = read_json(protocol_path), read_json(policy_path)
    if sha256(protocol_path) != policy["protocol_sha256"]:
        raise RuntimeError("Protocol changed after milestone policy was sealed")
    panel = pd.read_parquet(panel_path)
    minimum_symbols = int(policy["minimum_symbols"])
    dates = qualified_dates(panel, protocol, minimum_symbols)
    periods = completed_rebalance_periods(
        len(dates), int(policy["horizon_trading_days"]), int(policy["rebalance_every_trading_days"])
    )
    status, next_period = status_for(periods)
    counts = (
        panel.assign(timestamp=pd.to_datetime(panel["timestamp"], utc=True))
        .groupby("timestamp", observed=True)["symbol"].nunique()
    )
    report = {
        "report_version": "v009-shadow-monitor-1.0",
        "designation": status,
        "performance_blind": True,
        "contains_returns": False,
        "contains_sharpe": False,
        "contains_signal_ic": False,
        "qualified_market_dates": len(dates),
        "completed_non_overlapping_periods": periods,
        "next_milestone_periods": next_period,
        "minimum_symbols_required": minimum_symbols,
        "minimum_observed_symbols": int(counts.min()) if len(counts) else 0,
        "maximum_observed_symbols": int(counts.max()) if len(counts) else 0,
        "first_qualified_date": dates[0].isoformat() if dates else None,
        "last_qualified_date": dates[-1].isoformat() if dates else None,
        "panel_sha256": sha256(panel_path),
        "policy_sha256": sha256(policy_path),
        "official_lock_ready": periods >= 52,
        "official_lock_executed": False,
        "v57_unlocked": False,
        "champion_eligible": False,
        "live_trading_allowed": False,
    }
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    latest = write_json_atomic(output_dir / "latest_status.json", report)
    print(latest.read_text(encoding="utf-8"))
    for milestone in (13, 26, 52):
        milestone_path = output_dir / f"milestone_{milestone:02d}_sealed.json"
        if periods >= milestone and not milestone_path.exists():
            sealed_report = dict(report)
            sealed_report["sealed_at_milestone"] = milestone
            write_json_atomic(milestone_path, sealed_report, exclusive=True)
            digest = seal(milestone_path)
            print(f"SEALED milestone {milestone}: {milestone_path} ({digest})")


if __name__ == "__main__":
    main()
