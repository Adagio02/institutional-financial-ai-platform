param([string]$QuotePath = "data\research\quotes")
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
$env:FINAI_V51_QUOTE_PATH = $QuotePath
Write-Host "Running V5.1.1-V5.1.3 quote/microstructure pipeline..." -ForegroundColor Cyan
python .\scripts\run_v51_microstructure.py
if ($LASTEXITCODE -ne 0) { throw "V5.1.x execution failed." }
& .\scripts\verify_v51.ps1
if ($LASTEXITCODE -ne 0) { throw "V5.1.x verification failed." }
Write-Host "V5.1.x complete. Next stage: V5.2." -ForegroundColor Green

