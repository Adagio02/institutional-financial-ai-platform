# Registers a weekday after-close task for the daily research pipeline and removes the
# older weekly task if it exists.
# Usage (from the project root):  .\research_kit\schedule_daily.ps1                 (Mon-Fri 18:00)
#                                 .\research_kit\schedule_daily.ps1 -Time 18:30
# Remove it later with:           Unregister-ScheduledTask -TaskName "FinAI Research Daily" -Confirm:$false
param([string]$Time = "18:00")
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Virtual environment not found at $Python" }
if (Get-ScheduledTask -TaskName "FinAI Shadow Run" -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName "FinAI Shadow Run" -Confirm:$false
    Write-Host "Removed the old weekly 'FinAI Shadow Run' task (the daily task replaces it)."
}
$Action = New-ScheduledTaskAction -Execute $Python -Argument "-m research_kit daily" -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At $Time
# StartWhenAvailable: if the PC was off at 18:00, run as soon as it is on again.
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName "FinAI Research Daily" -Action $Action -Trigger $Trigger -Settings $Settings `
    -Description "After-close data update, shadow recording and evaluation" -Force | Out-Null
Write-Host "Scheduled 'FinAI Research Daily' Monday-Friday at $Time (local time)." -ForegroundColor Green
Write-Host "Log: research\shadow\run.log   Status: research\shadow\status.json"
