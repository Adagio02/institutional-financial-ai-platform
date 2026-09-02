$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

if (-not (Test-Path "artifacts\v483\v483_ic_report.json")) {
    throw "Missing V4.8.3 IC report. Run the complete V4.8 pipeline first."
}

Write-Host "Running V4.9.1 long/short ranking portfolio..." -ForegroundColor Cyan
python .\scripts\run_v491_ranking_portfolio.py
if ($LASTEXITCODE -ne 0) { throw "V4.9.1 failed." }

Write-Host "Running V4.9.2 risk/factor neutralization..." -ForegroundColor Cyan
python .\scripts\run_v492_neutralization.py
if ($LASTEXITCODE -ne 0) { throw "V4.9.2 failed." }

Write-Host "Running V4.9.3 turnover/cost-aware optimization..." -ForegroundColor Cyan
python .\scripts\run_v493_cost_optimization.py
if ($LASTEXITCODE -ne 0) { throw "V4.9.3 failed." }

if (-not (Test-Path "artifacts\v493\v493_report.json")) {
    throw "The final V4.9.3 report was not created."
}

Write-Host "V4.9 series completed. Next version: V5.0." -ForegroundColor Green
