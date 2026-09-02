param(
    [Parameter(Mandatory = $true)]
    [string]$CurrentVersion,

    [Parameter(Mandatory = $true)]
    [string]$NextVersion,

    [string]$ProjectRoot = "D:\Projects\institutional-financial-ai-platform",

    [string]$Remote = "origin",

    [string]$CommitMessage = "Complete version $CurrentVersion",

    [string]$VerificationScript = ""
)

$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,

        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }
}

function Get-VersionBranch {
    param([Parameter(Mandatory = $true)][string]$Version)

    $CleanVersion = $Version.Trim()
    if ($CleanVersion.StartsWith("v", [System.StringComparison]::OrdinalIgnoreCase)) {
        return "v$($CleanVersion.Substring(1))"
    }
    return "v$CleanVersion"
}

function Get-VerificationPath {
    param([Parameter(Mandatory = $true)][string]$Version)

    $Digits = ($Version -replace "^[vV]", "") -replace "\.", ""
    return "scripts\verify_v$Digits.ps1"
}

$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
if (-not (Test-Path (Join-Path $ProjectRoot "pyproject.toml"))) {
    throw "Project root is invalid: $ProjectRoot"
}

Set-Location $ProjectRoot

Invoke-Checked {
    git rev-parse --is-inside-work-tree | Out-Null
} "The project directory is not a Git repository."

Invoke-Checked {
    git remote get-url $Remote | Out-Null
} "Git remote '$Remote' does not exist."

$CurrentBranch = (git branch --show-current).Trim()
if ([string]::IsNullOrWhiteSpace($CurrentBranch)) {
    throw "Git is in detached-HEAD state. Switch to a branch first."
}

$ExpectedCurrentBranch = Get-VersionBranch -Version $CurrentVersion
if ($CurrentBranch -ne $ExpectedCurrentBranch) {
    Write-Host (
        "Current branch is '$CurrentBranch'; version branch would be " +
        "'$ExpectedCurrentBranch'. The current branch will be published as-is."
    ) -ForegroundColor Yellow
}

if ([string]::IsNullOrWhiteSpace($VerificationScript)) {
    $VerificationScript = Get-VerificationPath -Version $CurrentVersion
}

$VerificationPath = Join-Path $ProjectRoot $VerificationScript
if (-not (Test-Path $VerificationPath)) {
    throw "Verification script does not exist: $VerificationPath"
}

$Activate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $Activate) {
    . $Activate
}

Write-Host "Verifying version $CurrentVersion..." -ForegroundColor Cyan
& $VerificationPath
if ($LASTEXITCODE -ne 0) {
    throw "Version $CurrentVersion verification failed. Nothing was committed."
}

Write-Host "Staging project changes..." -ForegroundColor Cyan
Invoke-Checked { git add --all } "git add failed."

$StagedFiles = @(git -c core.quotePath=false diff --cached --name-only --diff-filter=ACMR)
$BlockedNames = @(
    ".env",
    ".env.local",
    "credentials.json",
    "secrets.json",
    "id_rsa",
    "id_ed25519"
)

foreach ($RelativePath in $StagedFiles) {
    $LeafName = Split-Path $RelativePath -Leaf
    if ($BlockedNames -contains $LeafName) {
        throw "Sensitive file is staged and will not be pushed: $RelativePath"
    }

    $LocalPath = Join-Path $ProjectRoot $RelativePath
    if ((Test-Path -LiteralPath $LocalPath) -and (Get-Item -LiteralPath $LocalPath).Length -gt 50MB) {
        throw "File exceeds 50 MB and will not be pushed automatically: $RelativePath"
    }
}

git diff --cached --quiet
$HasStagedChanges = $LASTEXITCODE -ne 0

if ($HasStagedChanges) {
    Write-Host "Committing version $CurrentVersion..." -ForegroundColor Cyan
    Invoke-Checked {
        git commit -m $CommitMessage
    } "git commit failed."
} else {
    Write-Host "No new changes to commit." -ForegroundColor Yellow
}

Write-Host "Pushing '$CurrentBranch' to '$Remote'..." -ForegroundColor Cyan
Invoke-Checked {
    git push --set-upstream $Remote $CurrentBranch
} "Pushing the completed version failed."

$NextBranch = Get-VersionBranch -Version $NextVersion
if ($NextBranch -eq $CurrentBranch) {
    throw "The next-version branch must differ from the current branch."
}

$LocalNextExists = $null -ne (git branch --list $NextBranch)
if ($LocalNextExists) {
    Invoke-Checked { git switch $NextBranch } "Could not switch to '$NextBranch'."
} else {
    git ls-remote --exit-code --heads $Remote $NextBranch | Out-Null
    $RemoteNextExists = $LASTEXITCODE -eq 0

    if ($RemoteNextExists) {
        Invoke-Checked {
            git switch --track "$Remote/$NextBranch"
        } "Could not track remote branch '$Remote/$NextBranch'."
    } else {
        Invoke-Checked {
            git switch --create $NextBranch
        } "Could not create next-version branch '$NextBranch'."
    }
}

Write-Host "Publishing next-version branch '$NextBranch'..." -ForegroundColor Cyan
Invoke-Checked {
    git push --set-upstream $Remote $NextBranch
} "Publishing the next-version branch failed."

Write-Host "Completed version $CurrentVersion was pushed." -ForegroundColor Green
Write-Host "Workspace is now on branch $NextBranch." -ForegroundColor Green
git status --short --branch

