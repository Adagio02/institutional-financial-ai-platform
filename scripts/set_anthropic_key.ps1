# Stores your Anthropic API key for Ask FinAI, encrypted with Windows DPAPI.
# Only your Windows account on this PC can decrypt it. It is never written to .env or Git.
#   powershell -ExecutionPolicy Bypass -File .\scripts\set_anthropic_key.ps1

$ErrorActionPreference = "Stop"
$Folder = Join-Path $env:LOCALAPPDATA "FinAI"
$Path = Join-Path $Folder "anthropic-credential.xml"
New-Item -ItemType Directory -Force -Path $Folder | Out-Null

$Secret = Read-Host "Paste your Anthropic API key (it will not be shown)" -AsSecureString
$Plain = [Net.NetworkCredential]::new("", $Secret).Password.Trim()
if (-not $Plain.StartsWith("sk-ant-")) {
    Remove-Variable Plain
    throw "That does not look like an Anthropic API key (it should start with sk-ant-). Nothing was saved."
}
$Clean = ConvertTo-SecureString $Plain -AsPlainText -Force
Remove-Variable Plain

if (Test-Path $Path) { Copy-Item $Path "$Path.old" -Force }
New-Object System.Management.Automation.PSCredential("anthropic", $Clean) | Export-Clixml -Path $Path
Write-Host "Saved (encrypted) to $Path"
Write-Host "Start Ask FinAI with:  powershell -ExecutionPolicy Bypass -File .\scripts\start_ask_finai.ps1"
