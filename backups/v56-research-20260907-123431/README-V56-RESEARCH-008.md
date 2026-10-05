# V5.6 Research 008: constraint-aligned residual target

V007 produced positive gross and net returns but Sharpe 0.151. Training calibration IC did not predict fold returns (rank correlation -0.287), so V008 does not use confidence scaling. Instead it aligns the learning target with the permitted portfolio: each date's future returns are residualized against sector indicators and lagged beta, and models learn the cross-sectional rank of that residual.

```powershell
Set-Location "D:\Projects\institutional-financial-ai-platform"
& ".\.venv\Scripts\Activate.ps1"
& ".\scripts\run_v56_research_008.ps1" `
 -InputPath ".\data\research\v56-research-005-enriched\model_panel.parquet" `
 -OutputPath ".\artifacts\v56-research-008" `
 -TransactionCostBps 5
```

Inspect:

```powershell
$R=Get-Content ".\artifacts\v56-research-008\research_report.json" -Raw|ConvertFrom-Json
$R|Select-Object eligible_to_freeze_candidate,mean_rebalance_residual_rank_ic,mean_rebalance_raw_rank_ic,active_fraction,gross_compounded_return,blocking_reasons,required_next_step|Format-List
$R.metrics|Format-List;$R.checks|Format-List
```

V008 is another development experiment on an already observed period. If it passes, freeze the complete policy and evaluate it exactly once on genuinely unseen real V5.6 locked data. Do not treat this report itself as permission to run V5.7.

```powershell
git switch -c v5.6-research-008
git add scripts/run_v56_research_008.py scripts/run_v56_research_008.ps1 src/finai/research/v56/models.py src/finai/research/v56/pipeline_v008.py tests/unit/test_v56_research_008.py README-V56-RESEARCH-008.md
git commit -m "Align V5.6 learning target with factor-neutral portfolio"
git push -u origin v5.6-research-008
```
