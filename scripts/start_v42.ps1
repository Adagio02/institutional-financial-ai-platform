$ErrorActionPreference = "Stop"


# ============================================================
# FINAI V4.2 AUTONOMOUS WORKSTATION STARTUP
# ============================================================


$Project = "D:\Projects\institutional-financial-ai-platform"

$PythonExe = Join-Path `
    $Project `
    ".venv\Scripts\python.exe"

$SupervisorScript = Join-Path `
    $Project `
    "scripts\run_v37_autonomous_platform.py"

$DashboardCompose = Join-Path `
    $Project `
    "docker-compose.v42.yml"

$Workspace = Join-Path `
    $Project `
    "FinAI-V42.code-workspace"

$ArtifactDirectory = Join-Path `
    $Project `
    "artifacts\v42"

$StartupLog = Join-Path `
    $ArtifactDirectory `
    "startup.log"

$SupervisorStdout = Join-Path `
    $ArtifactDirectory `
    "autonomous_stdout.log"

$SupervisorStderr = Join-Path `
    $ArtifactDirectory `
    "autonomous_stderr.log"


New-Item `
    -ItemType Directory `
    -Force `
    -Path $ArtifactDirectory |
Out-Null


Set-Location $Project


# ============================================================
# LOGGING
# ============================================================


function Write-StartupLog {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    $Timestamp = Get-Date `
        -Format "yyyy-MM-dd HH:mm:ss"

    $Line = "[$Timestamp] $Message"

    Write-Host $Line

    Add-Content `
        -Path $StartupLog `
        -Value $Line
}


# ============================================================
# DOCKER ENGINE
# ============================================================


function Test-DockerReady {
    try {
        docker info *> $null

        return (
            $LASTEXITCODE -eq 0
        )
    }
    catch {
        return $false
    }
}


function Start-DockerDesktop {
    if (Test-DockerReady) {
        Write-StartupLog `
            "Docker engine is already available."

        return
    }


    $Candidates = @(
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
    )


    $DockerDesktop = $null


    foreach ($Candidate in $Candidates) {
        if (Test-Path $Candidate) {
            $DockerDesktop = $Candidate
            break
        }
    }


    if (-not $DockerDesktop) {
        throw `
            "Docker Desktop executable could not be found."
    }


    Write-StartupLog `
        "Starting Docker Desktop."


    Start-Process `
        -FilePath $DockerDesktop


    $TimeoutSeconds = 240

    $StartedAt = Get-Date


    while (-not (Test-DockerReady)) {
        $Elapsed = (
            (Get-Date) - $StartedAt
        ).TotalSeconds


        if ($Elapsed -gt $TimeoutSeconds) {
            throw `
                "Docker engine did not become ready within $TimeoutSeconds seconds."
        }


        Start-Sleep `
            -Seconds 3
    }


    Write-StartupLog `
        "Docker engine is ready."
}


# ============================================================
# MAIN COMPOSE FILE
# ============================================================


function Get-MainComposeFile {
    $Candidates = @(
        (Join-Path $Project "docker-compose.yml"),
        (Join-Path $Project "docker-compose.yaml"),
        (Join-Path $Project "compose.yml"),
        (Join-Path $Project "compose.yaml")
    )


    foreach ($Candidate in $Candidates) {
        if (Test-Path $Candidate) {
            return $Candidate
        }
    }


    throw `
        "No main Docker Compose file was found."
}


# ============================================================
# MAIN INFRASTRUCTURE
# ============================================================


function Start-MainInfrastructure {
    $ComposeFile = Get-MainComposeFile


    Write-StartupLog `
        "Starting main FinAI Docker infrastructure."


    Push-Location $Project


    try {
        docker compose `
            -f $ComposeFile `
            up -d


        if ($LASTEXITCODE -ne 0) {
            throw `
                "Main docker compose startup failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }


    Write-StartupLog `
        "Main Docker infrastructure launch requested."
}


# ============================================================
# POSTGRES READINESS
# ============================================================


function Test-TcpPort {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ComputerName,

        [Parameter(Mandatory = $true)]
        [int]$Port
    )


    try {
        $Client = New-Object `
            System.Net.Sockets.TcpClient


        $Connection = $Client.BeginConnect(
            $ComputerName,
            $Port,
            $null,
            $null
        )


        $Connected = $Connection.AsyncWaitHandle.WaitOne(
            1000,
            $false
        )


        if (-not $Connected) {
            $Client.Close()

            return $false
        }


        $Client.EndConnect(
            $Connection
        )


        $Client.Close()


        return $true
    }
    catch {
        return $false
    }
}


function Wait-ForPostgres {
    $HostName = "127.0.0.1"

    $Port = 5433

    $TimeoutSeconds = 180

    $StartedAt = Get-Date


    Write-StartupLog `
        "Waiting for PostgreSQL on $HostName`:$Port."


    while ($true) {
        if (
            Test-TcpPort `
                -ComputerName $HostName `
                -Port $Port
        ) {
            Write-StartupLog `
                "PostgreSQL port $Port is available."

            return
        }


        $Elapsed = (
            (Get-Date) - $StartedAt
        ).TotalSeconds


        if ($Elapsed -gt $TimeoutSeconds) {
            Write-StartupLog `
                "Current Docker state:"

            docker ps -a


            throw `
                "PostgreSQL did not become available on port $Port within $TimeoutSeconds seconds."
        }


        Start-Sleep `
            -Seconds 3
    }
}


# ============================================================
# V4.2 DASHBOARD
# ============================================================


function Start-V42Dashboard {
    if (-not (Test-Path $DashboardCompose)) {
        throw `
            "Dashboard compose file does not exist: $DashboardCompose"
    }


    Write-StartupLog `
        "Starting FinAI V4.2 dashboard."


    Push-Location $Project


    try {
        docker compose `
            -f $DashboardCompose `
            up -d


        if ($LASTEXITCODE -ne 0) {
            throw `
                "Dashboard compose startup failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }


    Write-StartupLog `
        "V4.2 dashboard launch requested."
}


function Wait-ForDashboard {
    $Url = "http://127.0.0.1:3838"

    $TimeoutSeconds = 120

    $StartedAt = Get-Date


    Write-StartupLog `
        "Waiting for V4.2 dashboard."


    while ($true) {
        try {
            $Response = Invoke-WebRequest `
                -Uri $Url `
                -UseBasicParsing `
                -TimeoutSec 5


            if ($Response.StatusCode -eq 200) {
                Write-StartupLog `
                    "V4.2 dashboard is HTTP-ready."

                return
            }
        }
        catch {
        }


        $Elapsed = (
            (Get-Date) - $StartedAt
        ).TotalSeconds


        if ($Elapsed -gt $TimeoutSeconds) {
            Write-StartupLog `
                "Dashboard did not become ready before timeout."

            docker logs `
                finai-v42-dashboard `
                --tail 100

            return
        }


        Start-Sleep `
            -Seconds 3
    }
}


# ============================================================
# AUTONOMOUS SUPERVISOR
# ============================================================


function Get-AutonomousSupervisor {
    return (
        Get-CimInstance `
            Win32_Process |
        Where-Object {
            $_.Name -match "^python" -and
            $_.CommandLine -match `
                "run_v37_autonomous_platform\.py"
        }
    )
}


function Start-AutonomousSupervisor {
    if (-not (Test-Path $PythonExe)) {
        throw `
            "Python virtual environment was not found: $PythonExe"
    }


    if (-not (Test-Path $SupervisorScript)) {
        throw `
            "Autonomous supervisor script was not found: $SupervisorScript"
    }


    $Existing = Get-AutonomousSupervisor


    if ($Existing) {
        Write-StartupLog `
            "Autonomous supervisor is already running."

        return
    }


    Write-StartupLog `
        "Starting autonomous FinAI supervisor."


    if (Test-Path $SupervisorStdout) {
        Remove-Item `
            $SupervisorStdout `
            -Force
    }


    if (Test-Path $SupervisorStderr) {
        Remove-Item `
            $SupervisorStderr `
            -Force
    }


    Start-Process `
        -FilePath $PythonExe `
        -ArgumentList @(
        "-u",
        $SupervisorScript
    ) `
        -WorkingDirectory $Project `
        -WindowStyle Minimized `
        -RedirectStandardOutput $SupervisorStdout `
        -RedirectStandardError $SupervisorStderr


    Start-Sleep `
        -Seconds 5


    $Process = Get-AutonomousSupervisor


    if (-not $Process) {
        Write-StartupLog `
            "Autonomous supervisor exited during startup."

        if (Test-Path $SupervisorStderr) {
            Get-Content `
                $SupervisorStderr `
                -Tail 100
        }


        throw `
            "Autonomous supervisor is not running."
    }


    Write-StartupLog `
        "Autonomous supervisor is running."
}


# ============================================================
# VS CODE
# ============================================================


function Start-VSCode {
    $CodeCommand = Get-Command `
        "code" `
        -ErrorAction SilentlyContinue


    if (-not $CodeCommand) {
        Write-StartupLog `
            "VS Code CLI is not available in PATH."

        return
    }


    if (Test-Path $Workspace) {
        Write-StartupLog `
            "Opening FinAI V4.2 VS Code workspace."


        Start-Process `
            -FilePath "code" `
            -ArgumentList $Workspace `
            -WorkingDirectory $Project
    }
    else {
        Write-StartupLog `
            "Workspace file missing. Opening project folder."


        Start-Process `
            -FilePath "code" `
            -ArgumentList $Project `
            -WorkingDirectory $Project
    }
}


# ============================================================
# STATUS SUMMARY
# ============================================================


function Show-SystemStatus {
    Write-Host ""
    Write-Host "============================================"
    Write-Host " FINAI V4.2 SYSTEM STATUS"
    Write-Host "============================================"
    Write-Host ""


    docker ps `
        --format `
        "table {{.Names}}\t{{.Status}}\t{{.Ports}}"


    Write-Host ""
    Write-Host "PostgreSQL 5433:"


    $DatabaseReady = Test-TcpPort `
        -ComputerName "127.0.0.1" `
        -Port 5433


    Write-Host $DatabaseReady


    Write-Host ""
    Write-Host "Autonomous supervisor:"


    Get-AutonomousSupervisor |
    Select-Object `
        ProcessId,
    CommandLine


    Write-Host ""
    Write-Host "Dashboard:"
    Write-Host "http://127.0.0.1:3838"
    Write-Host ""
}


# ============================================================
# MAIN
# ============================================================


try {
    Write-StartupLog `
        "FinAI V4.2 autonomous startup beginning."


    Start-DockerDesktop


    Start-MainInfrastructure


    Wait-ForPostgres


    Start-V42Dashboard


    Wait-ForDashboard


    Start-AutonomousSupervisor


    Start-VSCode


    Show-SystemStatus


    Write-StartupLog `
        "FinAI V4.2 autonomous startup completed."
}
catch {
    Write-StartupLog (
        "STARTUP FAILURE: " +
        $_.Exception.Message
    )


    throw
}