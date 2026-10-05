# V009 provisional shadow milestones

This overlay adds performance-blind 13/26-period operational milestones while preserving the existing 52-period, one-shot V5.6 gate. It cannot guarantee promotion or profit.

## Integrity rules

- Interim reports contain no return, Sharpe, IC, or strategy-performance result.
- `provisional_shadow_champion` is an operational designation only.
- It never unlocks V5.7, champion eligibility, orders, or live trading.
- The active universe must have verified sector provenance and a matching attestation before sealing the policy.
- At 52 complete non-overlapping periods, the monitor reports readiness only. It does not execute the official lock.
- The existing `check_v009_unlock.py` remains unchanged.

## Install

```powershell
Set-Location "D:\Projects\institutional-financial-ai-platform"
& ".\.venv\Scripts\Activate.ps1"
$ExtractRoot = "$HOME\Downloads\finai-v009-provisional-shadow-milestones"
& "$ExtractRoot\v009_milestone_package\scripts\install_v009_milestones.ps1" -ProjectRoot (Get-Location).Path
$env:PYTHONPATH = (Join-Path (Get-Location).Path "src")
python -m pytest ".\tests\unit\test_v009_milestones.py" -q
```

## Sector prerequisite and immutable policy

Do not run this section while `classification_provenance` contains `seed_unverified`. After genuine verification, recreate the protocol so its universe hash matches and create the sector attestation. Then freeze the fitted candidate exactly once:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location).Path "src")
python ".\scripts\freeze_v009_candidate.py" `
  --panel ".\data\research\v009-reset\model_panel.parquet" `
  --model-audit ".\artifacts\v009-reset\model\audit.json" `
  --protocol ".\artifacts\v009-reset\protocol.json" `
  --universe ".\config\v009_universe.csv" `
  --sector-attestation ".\artifacts\v009-reset\sector_attestation.json" `
  --output ".\artifacts\v009-reset\frozen_candidate.joblib"
if ($LASTEXITCODE -ne 0) { throw "Candidate freeze failed." }
```

Seal the milestone policy:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location).Path "src")
python ".\scripts\create_v009_milestone_policy.py" `
  --protocol ".\artifacts\v009-reset\protocol.json" `
  --universe ".\config\v009_universe.csv" `
  --sector-attestation ".\artifacts\v009-reset\sector_attestation.json" `
  --candidate-model ".\artifacts\v009-reset\frozen_candidate.joblib" `
  --output ".\artifacts\v009-reset\milestone_policy.json"
if ($LASTEXITCODE -ne 0) { throw "Milestone policy creation failed." }
```

The policy is exclusive and immutable. Do not delete and recreate it to change rules after prospective collection begins.

## Install daily collection

```powershell
& ".\scripts\install_v009_daily_task.ps1" `
  -ProjectRoot (Get-Location).Path `
  -RunAt "5:30 PM"
```

This stores Alpaca credentials with Windows DPAPI under the current Windows user and registers a weekday Task Scheduler job. It works only under that same Windows account. Keep the credential XML and artifacts out of Git.

Test it:

```powershell
Start-ScheduledTask -TaskName "FinAI V009 Prospective Collection"
Start-Sleep -Seconds 15
Get-ScheduledTaskInfo -TaskName "FinAI V009 Prospective Collection" |
  Format-List LastRunTime,LastTaskResult,NextRunTime
```

`LastTaskResult` 0 is success. A holiday or missing completed bar is a normal no-data run when the collector exits cleanly.

## Inspect operational status

```powershell
if (Test-Path ".\artifacts\v009-shadow-monitoring\latest_status.json") {
  Get-Content ".\artifacts\v009-shadow-monitoring\latest_status.json" -Raw | ConvertFrom-Json | Format-List
}
Get-ChildItem ".\artifacts\v009-shadow-monitoring\milestone_*_sealed.json" -ErrorAction SilentlyContinue
```

Expected meanings:

- 13: `provisional_shadow_champion`, operational only.
- 26: `validated_shadow_monitoring`, operational only.
- 52: `official_lock_ready`; run the bundled official one-shot V5.6 locked evaluator exactly once.

## Official one-shot lock at 52

Only after `latest_status.json` says `official_lock_ready: true`, make a full backup and run:

```powershell
& ".\scripts\run_v009_official_lock.ps1"
```

It uses exactly the first 52 mature non-overlapping periods, records the attempt before scoring, and refuses an automatic second attempt. A failed gate is a legitimate result and must not be altered or rerun.

Then use the unchanged guard:

```powershell
python ".\scripts\check_v009_unlock.py" `
  --protocol ".\artifacts\v009-reset\protocol.json" `
  --locked-report ".\artifacts\v009-locked\v563_report.json" `
  --sector-attestation ".\artifacts\v009-reset\sector_attestation.json"
if ($LASTEXITCODE -ne 0) { throw "V5.7 remains locked." }
```

The official report must pass the original rules and sector-attestation hash check before V5.7 can unlock.

## Git

```powershell
git add src/finai/research/v56/v009_milestones.py scripts/create_v009_milestone_policy.py scripts/freeze_v009_candidate.py scripts/run_v009_milestone_monitor.py scripts/run_v009_official_lock.py scripts/run_v009_official_lock.ps1 scripts/run_v009_collection_and_monitor.ps1 scripts/scheduled_v009_collection.ps1 scripts/install_v009_daily_task.ps1 tests/unit/test_v009_milestones.py README-V009-MILESTONES.md
git commit -m "Add performance-blind V009 shadow milestones"
git push
```
