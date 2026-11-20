$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\Projects\institutional-financial-ai-platform"
$CredentialPath = Join-Path $env:LOCALAPPDATA "FinAI\alpaca-credential.xml"
$LogDirectory = Join-Path $ProjectRoot "logs\v009-prospective"

Set-Location $ProjectRoot
New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$LogPath = Join-Path $LogDirectory "collection-$Timestamp.log"

Start-Transcript -Path $LogPath

try {
    if (-not (Test-Path -LiteralPath $CredentialPath)) {
        throw "Encrypted Alpaca credential file is missing: $CredentialPath"
    }

    $Credential = Import-Clixml -LiteralPath $CredentialPath

    $env:APCA_API_KEY_ID = $Credential.UserName
    $env:APCA_API_SECRET_KEY = $Credential.GetNetworkCredential().Password
    $env:SEC_USER_AGENT = "Felipe Taruselli financial-research-project"

    $PythonPath = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

    if (-not (Test-Path -LiteralPath $PythonPath)) {
        throw "Virtual-environment Python is missing: $PythonPath"
    }

    & ".\scripts\run_v009_prospective_collect.ps1" `
        -ProtocolPath ".\artifacts\v009-reset\protocol.json" `
        -DataRoot ".\data\research\v009-prospective" `
        -MinimumSymbols 80

    if ($LASTEXITCODE -ne 0) {
        throw "V009 prospective collection returned exit code $LASTEXITCODE."
    }

    Write-Host "V009 collection completed safely." -ForegroundColor Green
}
catch {
    Write-Error $_
    exit 1
}
finally {
    Remove-Item Env:\APCA_API_KEY_ID -ErrorAction SilentlyContinue
    Remove-Item Env:\APCA_API_SECRET_KEY -ErrorAction SilentlyContinue
    Stop-Transcript
}
