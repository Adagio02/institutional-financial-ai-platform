$ErrorActionPreference = "Stop"

$project = (
    "D:\Projects\" +
    "institutional-financial-ai-platform"
)

Set-Location $project

& (
    Join-Path `
        $project `
        ".venv\Scripts\Activate.ps1"
)

docker compose up -d

if (
    $LASTEXITCODE -ne 0
) {
    throw "Docker Compose could not be started."
}

Start-Sleep `
    -Seconds 10

python -u `
    .\scripts\run_v37_autonomous_platform.py