$ErrorActionPreference = "Stop"

$Project = "D:\Projects\institutional-financial-ai-platform"

$Launcher = Join-Path `
    $Project `
    "scripts\start_v42.ps1"


if (-not (Test-Path $Launcher)) {
    throw "V4.2 launcher does not exist: $Launcher"
}


$StartupDirectory = [Environment]::GetFolderPath(
    "Startup"
)


if (-not (Test-Path $StartupDirectory)) {
    throw "Windows Startup directory was not found."
}


$StartupFile = Join-Path `
    $StartupDirectory `
    "FinAI-V42.cmd"


$Command = @"
@echo off
start "" powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Minimized -File "$Launcher"
"@


Set-Content `
    -Path $StartupFile `
    -Value $Command `
    -Encoding ASCII


Write-Host ""
Write-Host "FinAI V4.2 startup entry installed."
Write-Host ""
Write-Host "Startup file:"
Write-Host $StartupFile
Write-Host ""
Write-Host "Launcher:"
Write-Host $Launcher
Write-Host ""
Write-Host "FinAI V4.2 will launch when you sign into Windows."