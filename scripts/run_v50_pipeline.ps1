$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

if (-not (Test-Path "artifacts\v481")) {
    throw "Missing V4.8.1 artifacts. Run V4.8.1 before V5.0.x."
}

Write-Host "Running V5.0.1-V5.0.3 multi-strategy alpha library..." -ForegroundColor Cyan
python .\scripts\run_v50_alpha_library.py
if ($LASTEXITCODE -ne 0) { throw "V5.0.x execution failed." }

& .\scripts\verify_v50.ps1
if ($LASTEXITCODE -ne 0) { throw "V5.0.x verification failed." }
Write-Host "V5.0.x completed. Next stage: V5.1." -ForegroundColor Green

