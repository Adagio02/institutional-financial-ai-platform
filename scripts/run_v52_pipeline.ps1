param([string]$OptionPath = "data\research\options_chain")
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
$env:FINAI_V52_OPTION_PATH = $OptionPath

Write-Host "Running V5.2.1 option-chain normalization..." -ForegroundColor Cyan
python .\scripts\run_v521_option_normalization.py
if ($LASTEXITCODE -ne 0) { throw "V5.2.1 failed." }

Write-Host "Running V5.2.2 volatility-surface features..." -ForegroundColor Cyan
python .\scripts\run_v522_surface.py
if ($LASTEXITCODE -ne 0) { throw "V5.2.2 failed." }

Write-Host "Running V5.2.3 options/volatility signals..." -ForegroundColor Cyan
python .\scripts\run_v523_options_signals.py
if ($LASTEXITCODE -ne 0) { throw "V5.2.3 failed." }

& .\scripts\verify_v52.ps1
if ($LASTEXITCODE -ne 0) { throw "V5.2.x verification failed." }
Write-Host "V5.2.x complete. Next stage: V5.3." -ForegroundColor Green

