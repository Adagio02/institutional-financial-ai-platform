$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "publish_and_start_next_version.ps1") `
    -CurrentVersion "5.4.3" -NextBranch "v5.5" @args

