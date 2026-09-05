param(
 [string]$EnsemblePath = "artifacts\v54\v542_ensemble_signal",
 [double]$LongFraction = 0.20, [double]$TransactionCostBps = 5.0,
 [ValidateSet("real", "external_unverified", "synthetic", "demo", "test")][string]$Provenance = "external_unverified"
)
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
$env:FINAI_V55_ENSEMBLE_PATH = $EnsemblePath
$env:FINAI_V55_LONG_FRACTION = $LongFraction.ToString([Globalization.CultureInfo]::InvariantCulture)
$env:FINAI_V55_COST_BPS = $TransactionCostBps.ToString([Globalization.CultureInfo]::InvariantCulture)
$env:FINAI_V55_PROVENANCE = $Provenance
Write-Host "Running V5.5.1 purged walk-forward fold construction..." -ForegroundColor Cyan
python .\scripts\run_v551_folds.py
if ($LASTEXITCODE -ne 0) { throw "V5.5.1 failed." }
Write-Host "Running V5.5.2 out-of-sample portfolio simulation..." -ForegroundColor Cyan
python .\scripts\run_v552_simulation.py
if ($LASTEXITCODE -ne 0) { throw "V5.5.2 failed." }
Write-Host "Running V5.5.3 portfolio qualification..." -ForegroundColor Cyan
python .\scripts\run_v553_qualification.py
if ($LASTEXITCODE -ne 0) { throw "V5.5.3 failed." }
& .\scripts\verify_v55.ps1
if ($LASTEXITCODE -ne 0) { throw "V5.5.x verification failed." }
Write-Host "V5.5.x complete. Next stage: V5.6 locked validation." -ForegroundColor Green
