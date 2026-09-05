$ErrorActionPreference = "Continue"

$Project = "D:\Projects\institutional-financial-ai-platform"
$ComposeFile = Join-Path $Project "docker-compose.v42.yml"

Write-Host "Stopping FinAI V4.2..."


$Processes = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -match "^python" -and (
            $_.CommandLine -match "run_v37_autonomous_platform\.py" -or
            $_.CommandLine -match "run_v41_learning_cycle\.py" -or
            $_.CommandLine -match "run_v40_shadow_cycle\.py"
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
        docker compose `
            -f $ComposeFile `
            down
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Warning "Compose file not found: $ComposeFile"
}


Write-Host "FinAI V4.2 stopped."