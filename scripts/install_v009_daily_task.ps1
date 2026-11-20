param(
    [string]$ProjectRoot = "D:\Projects\institutional-financial-ai-platform",
    [string]$TaskName = "FinAI V009 Prospective Collection",
    [string]$RunAt = "5:30 PM"
)
$ErrorActionPreference = "Stop"
$CredentialDirectory = Join-Path $env:LOCALAPPDATA "FinAI"
New-Item -ItemType Directory -Force -Path $CredentialDirectory | Out-Null
$Key = Read-Host "Paste Alpaca API key ID"
$Secret = Read-Host "Paste Alpaca secret key" -AsSecureString
$Credential = [System.Management.Automation.PSCredential]::new($Key, $Secret)
$Credential | Export-Clixml (Join-Path $CredentialDirectory "alpaca-credential.xml")
$SecUserAgent = Read-Host "SEC User-Agent (your name and email)"
if ([string]::IsNullOrWhiteSpace($SecUserAgent) -or $SecUserAgent -notmatch "@") { throw "SEC User-Agent must include a contact email" }
$SecUserAgent.Trim() | Set-Content -LiteralPath (Join-Path $CredentialDirectory "sec-user-agent.txt") -Encoding UTF8
Remove-Variable Key, Secret, Credential
$ScriptPath = Join-Path $ProjectRoot "scripts\scheduled_v009_collection.ps1"
if (-not (Test-Path -LiteralPath $ScriptPath)) { throw "Scheduled wrapper missing: $ScriptPath" }
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`"" -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At $RunAt
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Performance-blind V009 collection and milestone monitoring." -Force | Out-Null
Write-Host "Registered $TaskName for weekdays at $RunAt." -ForegroundColor Green
