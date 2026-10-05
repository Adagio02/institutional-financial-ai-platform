# V5.6 Research 006 targeted portfolio repair

The supplied diagnostics established that V5.6 research 005 had positive model rank-IC but was inactive on more than 72% of rebalance dates. This overlay repairs construction; it does not guarantee or force a pass.

## Evidence-driven changes

- cross-sectional rank target instead of raw-return magnitude
- fold training/calibration/test separation
- model weights derived from the training fold's calibration tail only
- features selected for at least 60% coverage in the first training fold
- sparse V5.3 fundamentals automatically excluded rather than imputed across 94% missing rows
- deterministic sector-balanced top/bottom portfolios
- beta neutralization within the sector-neutral subspace
- volatility scaling, 5% position caps and 50% target/previous smoothing
- explicit construction status and active-fraction gate
- weekly Sharpe annualized with `sqrt(252 / 5)`, not `sqrt(252)`

## Run

```powershell
Set-Location "D:\Projects\institutional-financial-ai-platform"
& ".\.venv\Scripts\Activate.ps1"
& ".\scripts\run_v56_research_006.ps1" `
 -InputPath ".\data\research\v56-research-005-enriched\model_panel.parquet" `
 -OutputPath ".\artifacts\v56-research-006" `
 -MinimumSymbols 30 `
 -TransactionCostBps 5
```

## Inspect

```powershell
$R=Get-Content ".\artifacts\v56-research-006\research_report.json" -Raw|ConvertFrom-Json
$R|Select-Object eligible_to_create_new_locked_candidate,mean_oos_rank_ic,active_fraction,construction_status_counts,blocking_reasons|Format-List
$R.metrics|Format-List
$R.checks|Format-List
```

If it fails, preserve the result. Do not lower gates, flip the full OOS result, or use V5.7 for tuning. Research eligibility permits freezing a candidate; only a separate, genuinely untouched, one-shot V5.6 locked validation can authorize V5.7.

## Git

```powershell
git switch -c v5.6-research-006
git add requirements-v56-research.txt scripts/run_v56_research_006.py scripts/run_v56_research_006.ps1 src/finai/research/v56 tests/unit/test_v56_research.py tests/unit/test_v56_research_006.py README-V56-RESEARCH-006.md
git commit -m "Repair V5.6 portfolio construction and rank calibration"
git push -u origin v5.6-research-006
```
