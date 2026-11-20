# Registers a weekly Windows scheduled task that runs the shadow test.
# Usage (from the project root):  .\research_kit\schedule_shadow.ps1            (Saturdays 10:00)
#                                 .\research_kit\schedule_shadow.ps1 -Day Sunday -Time 09:00
# Remove it later with:           Unregister-ScheduledTask -TaskName "FinAI Shadow Run" -Confirm:$false
param([string]$Day = "Saturday", [string]$Time = "10:00")
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Virtual environment not found at $Python" }
$Action = New-ScheduledTaskAction -Execute $Python -Argument "-m research_kit shadow-run" -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Day -At $Time
# StartWhenAvailable: if the PC was off at the scheduled time, run as soon as it is on again.
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 3)
Register-ScheduledTask -TaskName "FinAI Shadow Run" -Action $Action -Trigger $Trigger -Settings $Settings `
    -Description "Weekly forward (shadow) test of frozen research strategies" -Force | Out-Null
Write-Host "Scheduled 'FinAI Shadow Run' every $Day at $Time. Log: research\shadow\run.log" -ForegroundColor Green
