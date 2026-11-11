$ErrorActionPreference = "Continue"

$Project = "D:\Projects\institutional-financial-ai-platform"
$ComposeFile = Join-Path $Project "docker-compose.v42.yml"

Write-Host "Stopping FinAI V4.2..."


$Processes = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -match "^python" -and (
            $_.CommandLine -match "run_v37_autonomous_platform\.py" -or
            $_.CommandLine -match "run_v41_learning_cycle\.py" -or
            $_.CommandLine -match "run_v40_shadow_cycle\.py" -or
            $_.CommandLine -match "ask_finai\\app\.py"
        )
    }


foreach ($Process in $Processes) {
    Write-Host "Stopping Python process $($Process.ProcessId)"

    Stop-Process `
        -Id $Process.ProcessId `
        -Force `
        -ErrorAction SilentlyContinue
}


if (Test-Path $ComposeFile) {
    Push-Location $Project

    try {
        # Remove only the dashboard container. "down" would also delete the network
        # shared with the main stack (same compose project), breaking Postgres & co.
        docker compose `
            -f $ComposeFile `
            rm --stop --force
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Warning "Compose file not found: $ComposeFile"
}


Write-Host "FinAI V4.2 stopped."