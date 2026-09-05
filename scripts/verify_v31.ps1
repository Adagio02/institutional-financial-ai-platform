$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================"
Write-Host "Version 3.1 verification"
Write-Host "========================================"
Write-Host ""

python --version

if ($LASTEXITCODE -ne 0) {
    throw "Python failed."
}

python -m compileall -q `
    src `
    tests `
    migrations `
    scripts

if ($LASTEXITCODE -ne 0) {
    throw "Compilation failed."
}

python -m ruff check `
    src `
    tests `
    migrations `
    scripts

if ($LASTEXITCODE -ne 0) {
    throw "Ruff failed."
}

python -m pytest `
    tests `
    -q `
    --timeout=120 `
    --basetemp="D:\finai-pytest\v31-verify" `
    -p no:cacheprovider

if ($LASTEXITCODE -ne 0) {
    throw "Tests failed."
}

$heads = @(
    alembic heads
)

$headCount = @(
    $heads |
        Where-Object {
            $_ -match "\(head\)"
        }
).Count

if ($headCount -ne 1) {
    throw "Expected one Alembic head."
}

Write-Host ""
Write-Host "========================================"
Write-Host "Version 3.1 verification passed."
Write-Host "========================================"
Write-Host ""