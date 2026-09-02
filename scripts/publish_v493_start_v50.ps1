$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "publish_and_start_next_version.ps1") `
    -CurrentVersion "4.9.3" `
    -NextBranch "v5.0" `
    @args

