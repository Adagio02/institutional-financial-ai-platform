param(
    [string]$FundamentalPath = "data\research\v53\fundamentals.csv",
    [string]$EventPath = "data\research\v53\events.csv",
    [string]$NewsPath = "data\research\v53\news.csv",
    [string]$PricePath = "data\research\v53\prices.csv",
    [ValidateSet("real", "external_unverified", "synthetic", "demo", "test")]
    [string]$Provenance = "external_unverified"
)
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
$env:FINAI_V53_FUNDAMENTAL_PATH = $FundamentalPath
$env:FINAI_V53_EVENT_PATH = $EventPath
$env:FINAI_V53_NEWS_PATH = $NewsPath
$env:FINAI_V53_PRICE_PATH = $PricePath
$env:FINAI_V53_PROVENANCE = $Provenance

Write-Host "Running V5.3.1 point-in-time data foundation..." -ForegroundColor Cyan
python .\scripts\run_v531_data.py
if ($LASTEXITCODE -ne 0) { throw "V5.3.1 failed." }
Write-Host "Running V5.3.2 fundamental/event/news features..." -ForegroundColor Cyan
python .\scripts\run_v532_features.py
if ($LASTEXITCODE -ne 0) { throw "V5.3.2 failed." }
Write-Host "Running V5.3.3 signal qualification and champion contract..." -ForegroundColor Cyan
python .\scripts\run_v533_signals.py
if ($LASTEXITCODE -ne 0) { throw "V5.3.3 failed." }
& .\scripts\verify_v53.ps1
if ($LASTEXITCODE -ne 0) { throw "V5.3.x verification failed." }
Write-Host "V5.3.x complete. Next stage: V5.4 alpha ensemble." -ForegroundColor Green

