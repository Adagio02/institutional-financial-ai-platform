$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

$Prerequisite = "artifacts\v483\v483_ic_report.json"
if (-not (Test-Path $Prerequisite)) {
    throw "Missing $Prerequisite. Run V4.8.3 first."
}

Write-Host "Running V4.9 portfolio construction engine..." -ForegroundColor Cyan
python .\scripts\run_v49_portfolio_engine.py
if ($LASTEXITCODE -ne 0) { throw "V4.9 failed." }

$Manifest = "artifacts\v49\v49_engine_manifest.json"
if (-not (Test-Path $Manifest)) { throw "V4.9 engine manifest was not created." }

Write-Host "V4.9 completed. Next stage: V4.9.1." -ForegroundColor Green
