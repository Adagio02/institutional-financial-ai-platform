# V5.6 Research 007: alpha-preserving factor-risk repair

V006 diagnostics showed +22.02% unconstrained gross return, +4.97% sector-neutral gross return, but -1.78% actual gross return. Exact beta neutralization and inverse-volatility reshaping—not signal direction—destroyed the demonstrated spread.

V007 therefore keeps equal-weight sector top/bottom legs, retains dollar and sector neutrality, changes exact zero beta into a predeclared absolute beta band of 0.10, and caps each rebalance's turnover at 0.25 through neutral-preserving interpolation. It reuses frozen V006 predictions so it changes portfolio construction only.

```powershell
Set-Location "D:\Projects\institutional-financial-ai-platform"
& ".\.venv\Scripts\Activate.ps1"
& ".\scripts\run_v56_research_007.ps1" `
 -PredictionPath ".\artifacts\v56-research-006\oos_predictions.parquet" `
 -OutputPath ".\artifacts\v56-research-007" `
 -TransactionCostBps 5
```

Inspect:

```powershell
$R=Get-Content ".\artifacts\v56-research-007\research_report.json" -Raw|ConvertFrom-Json
$R|Select-Object eligible_to_freeze_candidate,mean_rebalance_rank_ic,active_fraction,gross_compounded_return,blocking_reasons,required_next_step|Format-List
$R.metrics|Format-List;$R.checks|Format-List
```

This development window has already been observed. Even if V007 passes, it only permits freezing the V007 policy. It cannot serve as the new V5.6 lock and cannot authorize V5.7. The frozen policy must next face genuinely unseen real data exactly once.

Git:

```powershell
git switch -c v5.6-research-007
git add scripts/run_v56_research_007.py scripts/run_v56_research_007.ps1 src/finai/research/v56/portfolio_v007.py src/finai/research/v56/pipeline_v007.py tests/unit/test_v56_research_007.py README-V56-RESEARCH-007.md
git commit -m "Preserve sector alpha with bounded beta and turnover"
git push -u origin v5.6-research-007
```
