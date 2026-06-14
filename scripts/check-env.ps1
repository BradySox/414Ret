[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$failed = $false

function Write-Ok {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-WarnLine {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
    $script:failed = $true
}

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$repoPython = Join-Path $repoRoot ".python311\python.exe"

Write-Host "414Ret environment check"
Write-Host "Repo: $repoRoot"
Write-Host ""

if (Test-Path -LiteralPath $venvPython) {
    try {
        $venvInfo = & $venvPython -c "import sys; print(sys.version); print(sys.executable)" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $venvInfo) {
            throw "venv unusable"
        }
        $venvLines = @($venvInfo)
        if ($venvLines[0] -like "3.11*") {
            Write-Ok ".venv Python is usable: $($venvLines[0])"
        } else {
            Write-Fail ".venv is using the wrong Python version: $($venvLines[0])"
        }
    } catch {
        Write-Fail ".venv exists but could not be executed. Rebuild it with .\scripts\bootstrap-env.ps1"
    }
} else {
    Write-Fail ".venv\Scripts\python.exe is missing."
}

if (Test-Path -LiteralPath $repoPython) {
    try {
        $repoInfo = & $repoPython -c "import sys; print(sys.version)"
        Write-Ok "Repo-local embedded Python is present: $repoInfo"
    } catch {
        Write-WarnLine "Repo-local .python311 exists but could not be executed."
    }
} else {
    Write-WarnLine "Repo-local .python311 is not present."
}

try {
    $lfsVersion = git lfs version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Git LFS installed: $lfsVersion"
        $lfsEnv = git lfs env
        if ($lfsEnv -match "auth=none") {
            Write-WarnLine "Git LFS is unauthenticated for origin. GitHub uploads may fail until you re-auth."
        } else {
            Write-Ok "Git LFS auth looks configured."
        }
    } else {
        Write-Fail "Git LFS is not available."
    }
} catch {
    Write-Fail "Git LFS check failed."
}

try {
    $status = git status --short
    Write-Ok "Git status is readable."
    if ($status) {
        Write-WarnLine "Working tree is not clean:"
        foreach ($line in @($status)) {
            Write-Host "  $line"
        }
    }
} catch {
    Write-Fail "git status failed."
}

Write-Host ""
if ($failed) {
    Write-Host "Environment check finished with failures." -ForegroundColor Red
    exit 1
}

Write-Host "Environment check passed." -ForegroundColor Green
