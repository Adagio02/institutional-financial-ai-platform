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
