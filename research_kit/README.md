# research_kit

Pre-registered, one-shot research and forward (shadow) testing. Run everything from the
project root with the virtual environment active.

| Command | What it does |
|---|---|
| `python -m research_kit list` | Every hypothesis, how often it was tested, and its status |
| `python -m research_kit register <spec.json>` | Records a hypothesis BEFORE testing (spec is hashed) |
| `python -m research_kit build-events` | SEC earnings surprises + insider trades -> `model_panel_v2.parquet` |
| `python -m research_kit test <id>` | The single historical test; refuses to run twice |
| `python -m research_kit freeze <id> [--exploratory]` | Locks a strategy for forward testing |
| `python -m research_kit shadow-run` | Refreshes data and records new shadow portfolios (weekly) |
| `python -m research_kit shadow-report` | Scores shadow portfolios on data after the freeze |
| `python -m research_kit build-strategy-data` | ETF history for the cross-asset trend strategy (H3) |
| `python -m research_kit build-validation-data` | S&P 400 mid-caps (never in the S&P 500) for one-time validation |
| `python -m research_kit validate <id>` | Runs a passed calibration ONCE on the mid-caps |
| `python -m research_kit daily` | After-close pipeline: incremental data, health checks, recording, verdicts |

Daily automation
- `.\research_kit\schedule_daily.ps1` registers a Mon-Fri 18:00 task (replaces the weekly one).
- Or call `.\research_kit\run_daily_step.ps1` from your existing after-close script.
- Exit codes: 0 ok, 1 failed or data unhealthy (nothing recorded), 2 a strategy reached a final verdict.
- Outputs: `research/shadow/run.log`, `status.json`, `daily_summary.csv`, `<id>/report.json`, `<id>/ledger.csv`.
- Verdict rules (version 1, fixed): early retirement only for failure (from period 6: drawdown beyond
  2x the backtest's, or t < -2.5 versus the backtest); a positive verdict only at the planned length.

Rules this kit enforces
1. A hypothesis must be registered before it is tested, and cannot be edited afterwards.
2. Each hypothesis gets one historical test (`--force-reason` only for genuine bugs; the reason is logged).
3. Features in `research/policy.json` are closed for historical testing; ideas using only them go forward-only.
4. Only strategies that passed their historical test can be frozen as `qualified`.
5. Frozen strategies are never edited; shadow results count only data after the freeze date.
6. Promotion to champion is a human decision after enough forward evidence.

Commit the whole `research/` folder (registry, policy, frozen specs, results, shadow books): it is your evidence trail.
Do not commit `data/`.

Rule-based strategies (H3 trend, H4 momentum, H5 breakout) use `research_kit/strategies.py`.
They fit nothing to data, so a frozen strategy's results after its freeze date are a true
forward test; holdings are snapshotted daily in `research/shadow/<id>/book.parquet` for audit.

Calibration (H6, `research_kit/calibration.py`): a pre-registered grid of ATR stop multiples,
walk-forward selection (each year chosen from earlier years only, smoothed over grid neighbours),
a plateau check, and a single validation on mid-caps before freezing. Freezing a calibrated
strategy as qualified requires both a passed test and a passed validation.
