# Starts Ask FinAI (Claude chat for the FinAI platform) at http://127.0.0.1:8502
#   powershell -ExecutionPolicy Bypass -File .\scripts\start_ask_finai.ps1             (this window)
#   powershell -ExecutionPolicy Bypass -File .\scripts\start_ask_finai.ps1 -Background (hidden)
# Optional: set FINAI_CLAUDE_MODEL to use another Claude model (default claude-sonnet-5-5).

param(
    [switch]$Background,
    [int]$Port = 8502
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw ".venv not found at $Python" }

$KeyPath = Join-Path $env:LOCALAPPDATA "FinAI\anthropic-credential.xml"
if (-not (Test-Path $KeyPath)) {
    throw "No Anthropic key stored. Run .\scripts\set_anthropic_key.ps1 first."
}

$Existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($Existing) {
    Write-Host "Ask FinAI is already running: http://127.0.0.1:$Port"
    return
}

# The key lives only in this process's environment (and the Streamlit child it starts).
$env:ANTHROPIC_API_KEY = (Import-Clixml -Path $KeyPath).GetNetworkCredential().Password
$env:PYTHONPATH = Join-Path $ProjectRoot "src"
$env:FINAI_PROJECT_ROOT = $ProjectRoot

$Arguments = @(
    "-m", "streamlit", "run", (Join-Path $ProjectRoot "apps\ask_finai\app.py"),
    "--server.port", "$Port",
    "--server.address", "127.0.0.1",
    "--server.headless", "true",
    "--browser.gatherUsageStats", "false"
)

try {
    if ($Background) {
        $LogDir = Join-Path $ProjectRoot "logs\ask-finai"
        New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
        Start-Process -FilePath $Python -ArgumentList $Arguments -WorkingDirectory $ProjectRoot -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $LogDir "stdout.log") -RedirectStandardError (Join-Path $LogDir "stderr.log")
        Write-Host "Ask FinAI starting in the background: http://127.0.0.1:$Port"
    } else {
        Write-Host "Ask FinAI: http://127.0.0.1:$Port  (Ctrl+C to stop)"
        & $Python @Arguments
    }
}
finally {
    Remove-Item Env:\ANTHROPIC_API_KEY -ErrorAction SilentlyContinue
}
