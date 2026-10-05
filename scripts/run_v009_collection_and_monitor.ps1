param(
    [string]$ProtocolPath = ".\artifacts\v009-reset\protocol.json",
    [string]$PolicyPath = ".\artifacts\v009-reset\milestone_policy.json",
    [string]$DataRoot = ".\data\research\v009-prospective",
    [string]$MonitorOutput = ".\artifacts\v009-shadow-monitoring",
    [int]$MinimumSymbols = 80
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

& ".\scripts\run_v009_prospective_collect.ps1" `
    -ProtocolPath $ProtocolPath `
    -DataRoot $DataRoot `
    -MinimumSymbols $MinimumSymbols

if (-not $?) { throw "V009 prospective collection failed." }

$PanelPath = Join-Path $DataRoot "prospective_panel.parquet"
if (-not (Test-Path -LiteralPath $PanelPath)) {
    Write-Host "No prospective panel exists yet. Monitoring remains in collecting status." -ForegroundColor Yellow
    exit 0
}
if (-not (Test-Path -LiteralPath $PolicyPath)) {
    Write-Host "Milestone policy is not sealed yet; complete sector verification first." -ForegroundColor Yellow
    exit 0
}

$env:PYTHONPATH = Join-Path $ProjectRoot "src"
& ".\.venv\Scripts\python.exe" ".\scripts\run_v009_milestone_monitor.py" `
    --protocol $ProtocolPath `
    --policy $PolicyPath `
    --panel $PanelPath `
    --output $MonitorOutput

if ($LASTEXITCODE -ne 0) { throw "V009 milestone monitoring failed." }
