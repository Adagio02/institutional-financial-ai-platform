param([string]$Marker="artifacts\software-dry-run")
$ErrorActionPreference="Stop";$Root=(Resolve-Path(Join-Path $PSScriptRoot "..")).Path;Set-Location $Root
New-Item -ItemType Directory -Force -Path $Marker|Out-Null
$Record=[ordered]@{mode="software_dry_run";champion_eligible=$false;live_trading_allowed=$false;v57_data_gate_passed=$false;created_utc=(Get-Date).ToUniversalTime().ToString("o")}
$Record|ConvertTo-Json|Set-Content (Join-Path $Marker "qualification_status.json") -Encoding UTF8
python -m pytest tests -q
if($LASTEXITCODE-ne 0){throw "Project tests failed"}
Write-Host "V5.7-V5.9 software tests completed in ineligible dry-run mode." -ForegroundColor Green
