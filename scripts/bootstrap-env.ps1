[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[414Ret] $Message"
}

function Test-Python311 {
    param([string]$PythonPath)
    if (-not (Test-Path -LiteralPath $PythonPath)) {
        return $false
    }

    try {
        $version = & $PythonPath -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"
        return $version.Trim() -eq "3.11"
    } catch {
        return $false
    }
}

function Resolve-Python311 {
    $candidates = @(
        (Join-Path $PSScriptRoot "..\.python311\python.exe"),
        "C:\Users\brady\AppData\Local\Programs\Python\Python311\python.exe"
    )

    foreach ($candidate in $candidates) {
        $full = [System.IO.Path]::GetFullPath($candidate)
        if (Test-Python311 -PythonPath $full) {
            return $full
        }
    }

    try {
        $pyVersion = & py -3.11 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $pyVersion) {
            return $pyVersion.Trim()
        }
    } catch {
    }

    throw @"
Could not find a working Python 3.11 interpreter.

Tried:
  - repo-local .python311\python.exe
  - C:\Users\brady\AppData\Local\Programs\Python\Python311\python.exe
  - py -3.11

Install or repair Python 3.11 first, then rerun this script.
"@
}

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$venvDir = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$requirements = Join-Path $repoRoot "requirements.txt"

Write-Step "Locating Python 3.11..."
$python311 = Resolve-Python311
Write-Step "Using $python311"

if (Test-Path -LiteralPath $venvDir) {
    $rebuild = $Force
    if (-not $rebuild) {
        try {
            $venvVersion = & $venvPython -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2>$null
            $rebuild = $venvVersion.Trim() -ne "3.11"
        } catch {
            $rebuild = $true
        }
    }

    if ($rebuild) {
        Write-Step "Removing stale .venv..."
        Remove-Item -LiteralPath $venvDir -Recurse -Force
    }
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Step "Creating .venv..."
    & $python311 -m venv $venvDir
}

Write-Step "Upgrading pip..."
& $venvPython -m pip install --upgrade pip

Write-Step "Installing requirements..."
& $venvPython -m pip install -r $requirements

Write-Step "Done. Next run:"
Write-Host "  .\scripts\check-env.ps1"
