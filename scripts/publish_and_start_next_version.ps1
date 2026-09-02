param(
    [Parameter(Mandatory = $true)][string]$CurrentVersion,
    [Parameter(Mandatory = $true)][string]$NextBranch,
    [string]$Remote = "origin",
    [string]$CommitMessage = "Complete version $CurrentVersion",
    [switch]$SkipVerification,
    [switch]$AllowExistingNextBranch
)

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

git rev-parse --is-inside-work-tree | Out-Null
if ($LASTEXITCODE -ne 0) { throw "This directory is not a Git repository." }
$CurrentBranch = (git branch --show-current).Trim()
if ([string]::IsNullOrWhiteSpace($CurrentBranch)) { throw "Detached HEAD is not supported." }

if (-not $SkipVerification) {
    $VersionKey = $CurrentVersion.Replace(".", "")
    $VerifyScript = Join-Path $PSScriptRoot "verify_v$VersionKey.ps1"
    $VersionParts = $CurrentVersion.Split(".")
    if ((-not (Test-Path -LiteralPath $VerifyScript)) -and $VersionParts.Count -ge 2) {
        $SeriesKey = "$($VersionParts[0])$($VersionParts[1])"
        $VerifyScript = Join-Path $PSScriptRoot "verify_v$SeriesKey.ps1"
    }
    if (-not (Test-Path -LiteralPath $VerifyScript)) {
        throw "Verification script not found for $CurrentVersion. Use -SkipVerification only intentionally."
    }
    & $VerifyScript
}

# Do not parse git status paths. Quoted/non-ASCII filenames in porcelain output
# caused earlier Test-Path illegal-character failures. Git handles its own paths.
git add --all
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m $CommitMessage
    if ($LASTEXITCODE -ne 0) { throw "Git commit failed." }
} else {
    Write-Host "No new changes to commit." -ForegroundColor Yellow
}

git push --set-upstream $Remote $CurrentBranch
if ($LASTEXITCODE -ne 0) { throw "Push of $CurrentBranch failed." }

$Tag = "v$CurrentVersion"
git rev-parse --verify --quiet "refs/tags/$Tag" | Out-Null
if ($LASTEXITCODE -ne 0) {
    git tag -a $Tag -m "Version $CurrentVersion"
    git push $Remote $Tag
    if ($LASTEXITCODE -ne 0) { throw "Push of tag $Tag failed." }
}

git show-ref --verify --quiet "refs/heads/$NextBranch"
$LocalExists = $LASTEXITCODE -eq 0
git ls-remote --exit-code --heads $Remote $NextBranch | Out-Null
$RemoteExists = $LASTEXITCODE -eq 0
if (($LocalExists -or $RemoteExists) -and -not $AllowExistingNextBranch) {
    throw "Branch $NextBranch already exists. Re-run with -AllowExistingNextBranch to use it."
}
if ($LocalExists) {
    git switch $NextBranch
} elseif ($RemoteExists) {
    git switch --track "$Remote/$NextBranch"
} else {
    git switch -c $NextBranch
    git push --set-upstream $Remote $NextBranch
}
if ($LASTEXITCODE -ne 0) { throw "Could not switch to $NextBranch." }
Write-Host "Published $CurrentVersion and switched to $NextBranch." -ForegroundColor Green
