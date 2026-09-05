$ErrorActionPreference="Stop";&(Join-Path $PSScriptRoot "publish_and_start_next_version.ps1") -CurrentVersion "5.7.3" -NextBranch "v5.8" @args
