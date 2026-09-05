param([string]$LockedInputPath="data\research\v56\locked_input.csv",[double]$LongFraction=.20,[double]$TransactionCostBps=5,[ValidateSet("real","external_unverified","synthetic","demo","test")][string]$Provenance="external_unverified")
$ErrorActionPreference="Stop"; Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
$env:FINAI_V56_INPUT_PATH=$LockedInputPath; $env:FINAI_V56_LONG_FRACTION=$LongFraction.ToString([Globalization.CultureInfo]::InvariantCulture); $env:FINAI_V56_COST_BPS=$TransactionCostBps.ToString([Globalization.CultureInfo]::InvariantCulture); $env:FINAI_V56_PROVENANCE=$Provenance
Write-Host "Running V5.6.1 immutable lock creation..." -ForegroundColor Cyan; python .\scripts\run_v561_lock.py; if($LASTEXITCODE-ne 0){throw "V5.6.1 failed."}
Write-Host "Running V5.6.2 one-shot locked validation..." -ForegroundColor Cyan; python .\scripts\run_v562_locked_validation.py; if($LASTEXITCODE-ne 0){throw "V5.6.2 failed."}
Write-Host "Running V5.6.3 locked decision..." -ForegroundColor Cyan; python .\scripts\run_v563_decision.py; if($LASTEXITCODE-ne 0){throw "V5.6.3 failed."}
& .\scripts\verify_v56.ps1; if($LASTEXITCODE-ne 0){throw "V5.6 verification failed."}; Write-Host "V5.6 complete. Inspect eligibility before V5.7." -ForegroundColor Green
