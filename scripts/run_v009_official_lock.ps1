param(
    [string]$ProtocolPath = ".\artifacts\v009-reset\protocol.json",
    [string]$PolicyPath = ".\artifacts\v009-reset\milestone_policy.json",
    [string]$CandidateModel = ".\artifacts\v009-reset\frozen_candidate.joblib",
    [string]$SectorAttestation = ".\artifacts\v009-reset\sector_attestation.json",
    [string]$PanelPath = ".\data\research\v009-prospective\prospective_panel.parquet",
    [string]$Output = ".\artifacts\v009-locked"
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root
$env:PYTHONPATH = Join-Path $Root "src"
Write-Warning "This consumes the single official V009 locked attempt. Run only when official_lock_ready is true."
& ".\.venv\Scripts\python.exe" ".\scripts\run_v009_official_lock.py" --protocol $ProtocolPath --policy $PolicyPath --candidate-model $CandidateModel --sector-attestation $SectorAttestation --panel $PanelPath --output $Output
if ($LASTEXITCODE -ne 0) { throw "Official V009 locked evaluation failed or remains unavailable." }
