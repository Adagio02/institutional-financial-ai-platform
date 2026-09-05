param(
    [string]$PriceAlphaPath = "artifacts\v50\v50_alpha_signal_panel",
    [string]$MicroAlphaPath = "artifacts\v51\v512_microstructure_signals",
    [string]$OptionsAlphaPath = "artifacts\v52\v523_options_signals",
    [string]$FundamentalAlphaPath = "artifacts\v53\v533_fundamental_event_news_signals",
    [string]$TargetPath = "artifacts\v53\v533_fundamental_event_news_signals",
    [ValidateSet("real", "external_unverified", "synthetic", "demo", "test")]
    [string]$Provenance = "external_unverified"
)
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
$env:FINAI_V54_PRICE_ALPHA_PATH = $PriceAlphaPath
$env:FINAI_V54_MICRO_ALPHA_PATH = $MicroAlphaPath
$env:FINAI_V54_OPTIONS_ALPHA_PATH = $OptionsAlphaPath
$env:FINAI_V54_FUNDAMENTAL_ALPHA_PATH = $FundamentalAlphaPath
$env:FINAI_V54_TARGET_PATH = $TargetPath
$env:FINAI_V54_PROVENANCE = $Provenance

Write-Host "Running V5.4.1 multi-family signal alignment..." -ForegroundColor Cyan
python .\scripts\run_v541_alignment.py
if ($LASTEXITCODE -ne 0) { throw "V5.4.1 failed." }
Write-Host "Running V5.4.2 expanding alpha ensemble..." -ForegroundColor Cyan
python .\scripts\run_v542_ensemble.py
if ($LASTEXITCODE -ne 0) { throw "V5.4.2 failed." }
Write-Host "Running V5.4.3 ensemble qualification..." -ForegroundColor Cyan
python .\scripts\run_v543_qualification.py
if ($LASTEXITCODE -ne 0) { throw "V5.4.3 failed." }
& .\scripts\verify_v54.ps1
if ($LASTEXITCODE -ne 0) { throw "V5.4.x verification failed." }
Write-Host "V5.4.x complete. Next stage: V5.5." -ForegroundColor Green

