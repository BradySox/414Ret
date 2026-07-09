[CmdletBinding()]
param(
    # Also run `npm ci` first. Needed on a fresh checkout, or after client/package-lock.json
    # changed. Otherwise the existing client/node_modules is reused (faster).
    [switch]$Install
)

# Rebuild the web-map client bundle (client/build) that the desktop app serves.
#
# The Python/server side of the fork updates on a plain `git pull`, but the React/Leaflet
# UI (the map, the campaign-status ribbon, the map-layers panel) is a *prebuilt* bundle
# under client/build -- so any client change stays invisible in a source run until the
# bundle is recompiled. The rolling `latest` release ZIP is already built this way by CI
# (.github/actions/build-app), so this script is only for running from a source checkout.
#
# Run it after pulling main when the map UI looks stale, then restart Retribution.

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[414Ret] $Message"
}

# scripts/ -> repo root.
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ClientDir = Join-Path $RepoRoot "client"

if (-not (Test-Path -LiteralPath (Join-Path $ClientDir "package.json"))) {
    throw "No client/ found at $ClientDir -- run this from inside the 414Ret repo."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm not found. Install Node.js 24 (https://nodejs.org/) and re-run."
}

Push-Location $ClientDir
try {
    if ($Install -or -not (Test-Path -LiteralPath (Join-Path $ClientDir "node_modules"))) {
        Write-Step "Installing client dependencies (npm ci)..."
        npm ci
        if ($LASTEXITCODE -ne 0) { throw "npm ci failed (exit $LASTEXITCODE)." }
    }

    Write-Step "Building the web client (this takes a few minutes)..."
    # CI=false so react-scripts does not treat lint warnings as build errors locally
    # (CI itself keeps them strict; this is just for a dev source build).
    $env:CI = "false"
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "npm run build failed (exit $LASTEXITCODE)." }

    Write-Step "Done -- client/build refreshed. Restart Retribution to see the new UI."
}
finally {
    Pop-Location
}
