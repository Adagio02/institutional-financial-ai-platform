$ErrorActionPreference = "Stop"

$stopFile = (
    ".\artifacts\v37\STOP"
)

New-Item `
    -ItemType Directory `
    -Force `
    .\artifacts\v37 |
    Out-Null

New-Item `
    -ItemType File `
    -Force `
    $stopFile |
    Out-Null

Write-Host ""
Write-Host `
    "V3.7 KILL SWITCH ENABLED." `
    -ForegroundColor Red

Write-Host `
    "Autonomous operations will remain paused."