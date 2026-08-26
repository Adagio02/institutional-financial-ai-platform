$ErrorActionPreference = "Stop"

$stopFile = (
    ".\artifacts\v37\STOP"
)

if (
    Test-Path $stopFile
) {
    Remove-Item `
        $stopFile `
        -Force
}

Write-Host ""
Write-Host `
    "V3.7 kill switch cleared." `
    -ForegroundColor Green

Write-Host `
    "Autonomous operations may resume."