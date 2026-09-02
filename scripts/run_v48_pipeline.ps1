$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

Write-Host "Running V4.8 cross-sectional feature platform..." -ForegroundColor Cyan
python .\scripts\run_v48_feature_platform.py
if ($LASTEXITCODE -ne 0) { throw "V4.8 failed." }

Write-Host "Running V4.8.1 neutral targets..." -ForegroundColor Cyan
python .\scripts\run_v481_neutral_targets.py
if ($LASTEXITCODE -ne 0) { throw "V4.8.1 failed." }

Write-Host "Running V4.8.2 ranking models..." -ForegroundColor Cyan
python .\scripts\run_v482_ranking_models.py
if ($LASTEXITCODE -ne 0) { throw "V4.8.2 failed." }

Write-Host "Running V4.8.3 signal IC analysis..." -ForegroundColor Cyan
python .\scripts\run_v483_signal_ic_analysis.py
if ($LASTEXITCODE -ne 0) { throw "V4.8.3 failed." }

Write-Host "V4.8 through V4.8.3 completed." -ForegroundColor Green
