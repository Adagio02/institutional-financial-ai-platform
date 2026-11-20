param(
    [string]$ProtocolPath =
    "artifacts\v009-reset\protocol.json",

    [string]$DataRoot =
    "data\research\v009-prospective",

    [int]$MinimumSymbols = 80
)

$ErrorActionPreference = "Stop"

$Root = (
    Resolve-Path (
        Join-Path $PSScriptRoot ".."
    )
).Path

Set-Location $Root

foreach ($Name in @(
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "SEC_USER_AGENT"
    )) {
    $Value = [Environment]::GetEnvironmentVariable($Name)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "$Name is not loaded."
    }
}

if (-not (Test-Path -LiteralPath $ProtocolPath)) {
    throw "Protocol not found: $ProtocolPath"
}

$Protocol = Get-Content `
    -LiteralPath $ProtocolPath `
    -Raw |
ConvertFrom-Json

$LockStart = [datetime]$Protocol.prospective_lock_start
$Today = (Get-Date).Date

if ($Today -lt $LockStart.Date) {
    Write-Host (
        "Prospective collection has not started. Start: " +
        $LockStart.ToString("yyyy-MM-dd")
    ) -ForegroundColor Yellow

    exit 0
}

$Lookback = $LockStart.AddDays(-550).ToString("yyyy-MM-dd")
$End = $Today.ToString("yyyy-MM-dd")
$Universe = "config\v009_universe.csv"

$Bars = Join-Path $DataRoot "bars_with_lookback.parquet"
$Sec = Join-Path $DataRoot "sec"
$Panel = Join-Path $DataRoot "prospective_panel.parquet"

python ".\scripts\acquire_v56r005_bars.py" `
    --universe $Universe `
    --start $Lookback `
    --end $End `
    --output $Bars

if ($LASTEXITCODE -ne 0) {
    throw "Prospective bars failed."
}

$env:FINAI_CHECK_BARS = (
    Resolve-Path $Bars
).Path

$env:FINAI_CHECK_START = $LockStart.ToString("yyyy-MM-dd")

$CoverageOutput = @'
import os
import pandas as pd

bars = pd.read_parquet(os.environ["FINAI_CHECK_BARS"])
bars["timestamp"] = pd.to_datetime(bars["timestamp"], utc=True)

start = pd.Timestamp(
    os.environ["FINAI_CHECK_START"],
    tz="UTC",
)

prospective = bars[bars["timestamp"] >= start]

if prospective.empty:
    print("NOT_READY")
else:
    counts = prospective.groupby("timestamp")["symbol"].nunique()
    print(f"READY|{int(counts.max())}|{len(counts)}")
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Prospective coverage inspection failed."
}

$CoverageResult = (
    $CoverageOutput |
    Select-Object -Last 1
).Trim()

if ($CoverageResult -eq "NOT_READY") {
    Write-Host (
        "No completed daily bars exist on or after " +
        $LockStart.ToString("yyyy-MM-dd") +
        ". Nothing was evaluated."
    ) -ForegroundColor Yellow

    exit 0
}

$Parts = $CoverageResult -split "\|"
$MaximumSymbols = [int]$Parts[1]
$AvailableDates = [int]$Parts[2]

if ($MaximumSymbols -lt $MinimumSymbols) {
    Write-Host (
        "Prospective data exists, but maximum coverage is " +
        "$MaximumSymbols symbols; protocol requires " +
        "$MinimumSymbols. Panel was not evaluated."
    ) -ForegroundColor Yellow

    exit 0
}

python ".\scripts\acquire_v009_sec.py" `
    --universe $Universe `
    --output $Sec

if ($LASTEXITCODE -ne 0) {
    throw "Prospective SEC refresh failed."
}

python ".\scripts\build_v009_panel.py" `
    --bars $Bars `
    --universe $Universe `
    --fundamentals (Join-Path $Sec "fundamentals.parquet") `
    --events (Join-Path $Sec "filing_events.parquet") `
    --output $Panel `
    --minimum-symbols $MinimumSymbols `
    --output-start ($LockStart.ToString("yyyy-MM-dd"))

if ($LASTEXITCODE -ne 0) {
    throw "Prospective panel failed."
}

python ".\scripts\collect_v009_prospective.py" `
    --protocol $ProtocolPath

Write-Host (
    "Prospective data refreshed without evaluating returns: " +
    $Panel
) -ForegroundColor Green