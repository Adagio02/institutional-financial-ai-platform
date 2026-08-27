$ErrorActionPreference = "Stop"

$Project = "D:\Projects\institutional-financial-ai-platform"
$ComposeFile = Join-Path $Project "docker-compose.v42.yml"
$Workspace = Join-Path $Project "FinAI-V42.code-workspace"
$SupervisorScript = Join-Path $Project "scripts\run_v37_autonomous_platform.py"
$PythonExe = Join-Path $Project ".venv\Scripts\python.exe"
$LogDirectory = Join-Path $Project "artifacts\v42"
$LogFile = Join-Path $LogDirectory "startup.log"

New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null


function Write-StartupLog {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $Line = "[$Timestamp] $Message"

    Write-Host $Line
    Add-Content -Path $LogFile -Value $Line
}


function Test-DockerReady {
    try {
        docker info *> $null

        if ($LASTEXITCODE -eq 0) {
            return $true
        }

        return $false
    }
    catch {
        return $false
    }
}


function Start-DockerDesktop {
    if (Test-DockerReady) {
        Write-StartupLog "Docker is already running."
        return
    }

    $DockerCandidates = @(
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
    )

    $DockerDesktop = $null

    foreach ($Candidate in $DockerCandidates) {
        if (Test-Path $Candidate) {
            $DockerDesktop = $Candidate
            break
        }
    }

    if (-not $DockerDesktop) {
        throw "Docker Desktop executable was not found."
    }

    Write-StartupLog "Starting Docker Desktop."

    Start-Process -FilePath $DockerDesktop

    $TimeoutSeconds = 180
    $StartedAt = Get-Date

    while (-not (Test-DockerReady)) {
        $Elapsed = ((Get-Date) - $StartedAt).TotalSeconds

        if ($Elapsed -gt $TimeoutSeconds) {
            throw "Docker did not become ready within $TimeoutSeconds seconds."
        }

        Start-Sleep -Seconds 3
    }

    Write-StartupLog "Docker is ready."
}


function Start-V42Dashboard {
    if (-not (Test-Path $ComposeFile)) {
        throw "V4.2 compose file not found: $ComposeFile"
    }

    Write-StartupLog "Starting V4.2 dashboard."

    Push-Location $Project

    try {
        docker compose -f $ComposeFile up -d

        if ($LASTEXITCODE -ne 0) {
            throw "docker compose returned exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }

    Write-StartupLog "V4.2 dashboard started."
}


function Start-AutonomousPlatform {
    if (-not (Test-Path $PythonExe)) {
        Write-StartupLog "Virtual environment Python not found. Skipping autonomous platform."
        return
    }

    if (-not (Test-Path $SupervisorScript)) {
        Write-StartupLog "Autonomous supervisor script not found. Skipping."
        return
    }

    $ExistingProcesses = Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -match "^python" -and
            $_.CommandLine -match "run_v37_autonomous_platform\.py"
        }

    if ($ExistingProcesses) {
        Write-StartupLog "Autonomous platform is already running."
        return
    }

    Write-StartupLog "Starting autonomous platform."

    Start-Process `
        -FilePath $PythonExe `
        -ArgumentList @(
            "-u",
            $SupervisorScript
        ) `
        -WorkingDirectory $Project `
        -WindowStyle Minimized

    Write-StartupLog "Autonomous platform launch requested."
}


function Start-VSCode {
    $CodeCommand = Get-Command "code" -ErrorAction SilentlyContinue

    if (-not $CodeCommand) {
        Write-StartupLog "VS Code command 'code' was not found in PATH."
        return
    }

    if (Test-Path $Workspace) {
        Write-StartupLog "Opening FinAI V4.2 workspace."

        Start-Process `
            -FilePath "code" `
            -ArgumentList $Workspace `
            -WorkingDirectory $Project
    }
    else {
        Write-StartupLog "Workspace file not found. Opening project directory."

        Start-Process `
            -FilePath "code" `
            -ArgumentList $Project `
            -WorkingDirectory $Project
    }
}


function Wait-ForDashboard {
    $Url = "http://localhost:3838"
    $TimeoutSeconds = 90
    $StartedAt = Get-Date

    Write-StartupLog "Waiting for dashboard HTTP service."

    while ($true) {
        try {
            $Response = Invoke-WebRequest `
                -Uri $Url `
                -UseBasicParsing `
                -TimeoutSec 5

            if ($Response.StatusCode -eq 200) {
                Write-StartupLog "Dashboard HTTP service is ready."
                return
            }
        }
        catch {
        }

        $Elapsed = ((Get-Date) - $StartedAt).TotalSeconds

        if ($Elapsed -gt $TimeoutSeconds) {
            Write-StartupLog "Dashboard did not become HTTP-ready within $TimeoutSeconds seconds."
            return
        }

        Start-Sleep -Seconds 3
    }
}


function Open-Dashboard {
    $Url = "http://localhost:3838"

    Write-StartupLog "Opening V4.2 dashboard."
    Start-Process $Url
}


try {
    Write-StartupLog "FinAI V4.2 startup beginning."

    Set-Location $Project

    Start-DockerDesktop
    Start-V42Dashboard
    Start-AutonomousPlatform
    Start-VSCode
    Wait-ForDashboard
    Open-Dashboard

    Write-StartupLog "FinAI V4.2 startup completed."
}
catch {
    Write-StartupLog ("STARTUP FAILURE: " + $_.Exception.Message)
    throw
}