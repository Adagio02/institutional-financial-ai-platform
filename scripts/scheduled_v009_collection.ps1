$ErrorActionPreference = "Stop"
$ProjectRoot = "D:\Projects\institutional-financial-ai-platform"
$CredentialPath = Join-Path $env:LOCALAPPDATA "FinAI\alpaca-credential.xml"
$SecUserAgentPath = Join-Path $env:LOCALAPPDATA "FinAI\sec-user-agent.txt"
$LogDirectory = Join-Path $ProjectRoot "logs\v009-prospective"
Set-Location $ProjectRoot
$env:VIRTUAL_ENV = Join-Path $ProjectRoot ".venv"
$env:PATH = (Join-Path $ProjectRoot ".venv\Scripts") + ";" + $env:PATH
New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null
$LogPath = Join-Path $LogDirectory ("collection-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")
Start-Transcript -Path $LogPath
try {
    if (-not (Test-Path -LiteralPath $CredentialPath)) { throw "Credential file missing: $CredentialPath" }
    $Credential = Import-Clixml -LiteralPath $CredentialPath
    $env:APCA_API_KEY_ID = $Credential.UserName
    $env:APCA_API_SECRET_KEY = $Credential.GetNetworkCredential().Password
    if (-not (Test-Path -LiteralPath $SecUserAgentPath)) { throw "SEC User-Agent file missing: $SecUserAgentPath" }
    $env:SEC_USER_AGENT = (Get-Content -LiteralPath $SecUserAgentPath -Raw).Trim()
    if ([string]::IsNullOrWhiteSpace($env:SEC_USER_AGENT)) { throw "SEC User-Agent is empty" }
    & ".\scripts\run_v009_collection_and_monitor.ps1"
    if (-not $?) { throw "Collection/monitoring failed" }
}
finally {
    Remove-Item Env:\APCA_API_KEY_ID -ErrorAction SilentlyContinue
    Remove-Item Env:\APCA_API_SECRET_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:\SEC_USER_AGENT -ErrorAction SilentlyContinue
    Stop-Transcript
}
