$ErrorActionPreference="Stop";&(Join-Path $PSScriptRoot "publish_and_start_next_version.ps1") -CurrentVersion "5.6.3" -NextBranch "v5.7" @args
