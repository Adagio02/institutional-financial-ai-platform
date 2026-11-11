# Legacy: V4.1 intraday learning loop

Status: **legacy** (marked 2026-11-11). Kept running and fully preserved for reference.

## What it is
The V3.7/V4.2 autonomous supervisor (`scripts/run_v37_autonomous_platform.py`) runs the
V4.1 learning cycle (`scripts/run_v41_learning_cycle.py`) on:

- a single symbol (`v41_learning_symbol`, AAPL)
- 1-minute bars (`v41_learning_interval = "1m"`)
- a 5-bar (5-minute) forward horizon (`v34_forward_horizon_bars = 5`)
- 4 bps round-trip costs

## Why it is legacy
Five-minute direction on one stock is close to a coin flip, and the resulting candidates
trade often enough (about 1,400+ trades per holdout) that costs dominate. Its candidates
have consistently failed the historical gate (for example holdout returns of -11% to -29%).

## Where the primary research lives
- V5.6 research 005-008: daily, cross-sectional, cost-aware, purged walk-forward research
  (`src/finai/research/v56`, `artifacts/v56-research-*`).
- V009: the frozen candidate's performance-blind prospective test
  (`artifacts/v009-reset`, `artifacts/v009-shadow-monitoring`).
- Forward shadow tests H0/H3/H5 (`research/shadow`).

The dashboard opens on **Research Program**; the old Executive page is now
**Legacy Intraday (V4.1)**.

## What did not change
No V4.1 code, configuration, artifacts or history were modified or deleted. Its gates
are unchanged. To retire it completely later, set `V37_AUTONOMOUS_ENABLED=false`
in `.env` (this also stops the supervisor's other jobs, so review first).
