$ErrorActionPreference="Stop"
$Project=(Get-Location).Path
if(-not(Test-Path (Join-Path $Project "src\finai"))){throw "Run this installer from the institutional-financial-ai-platform project root."}
$Payload=Join-Path $PSScriptRoot "payload"
Copy-Item (Join-Path $Payload "scripts\*") (Join-Path $Project "scripts") -Force
Write-Host "Installed V5.3 real-data acquisition scripts." -ForegroundColor Green
