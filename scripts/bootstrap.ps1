# ============================================================================
# Miori Core - bootstrap (Windows / PowerShell)
# Sets up env files, Python venv, and frontend deps.
#
# Usage:
#   scripts\bootstrap.ps1
#   scripts\bootstrap.ps1 -Full
# ============================================================================
param(
  [switch]$Full
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

function Find-Python {
  foreach ($name in @("python", "python3", "py")) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if (-not $cmd) { continue }
    $src = $cmd.Source
    if ($name -eq "py") { $src = "py -3" }
    try {
      & $cmd.Source -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" 2>$null
      if ($LASTEXITCODE -eq 0) { return $cmd.Source }
    } catch {}
  }
  return $null
}

function Copy-EnvIfMissing {
  if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
    Write-Host "   created .env from .env.example"
  }
  $apiEnv = "services/core-api/.env"
  $apiExample = "services/core-api/.env.example"
  if (-not (Test-Path $apiEnv) -and (Test-Path $apiExample)) {
    Copy-Item $apiExample $apiEnv
    Write-Host "   created services/core-api/.env from .env.example"
  }
}

Write-Host "-> Miori Core bootstrap"
Write-Host "   repo: $Root"

Write-Host ""
Write-Host "-> Configuration"
Copy-EnvIfMissing

Write-Host ""
Write-Host "-> Backend (services/core-api)"

$py = Find-Python
if (-not $py) {
  Write-Error "Python 3.11+ not found. Install from https://www.python.org/downloads/ and re-run."
}

$pyVer = (& $py -c "import sys; print('%d.%d.%d' % sys.version_info[:3])") 2>$null
Write-Host "   using $pyVer ($py)"

$cacheRoot = Join-Path $Root ".cache"
$pipCache = Join-Path $cacheRoot "pip"
$tmpDir = Join-Path $cacheRoot "tmp"
New-Item -ItemType Directory -Force -Path $pipCache, $tmpDir | Out-Null
$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"
$env:PIP_DEFAULT_TIMEOUT = "120"
$env:PIP_CACHE_DIR = $pipCache
$env:TMP = $tmpDir
$env:TEMP = $tmpDir

Push-Location services/core-api
$venvPy = ".\.venv\Scripts\python.exe"
$wantVer = (& $py -c "import sys; print('%d.%d.%d' % sys.version_info[:3])")

$recreate = $false
if (Test-Path $venvPy) {
  $haveVer = (& $venvPy -c "import sys; print('%d.%d.%d' % sys.version_info[:3])") 2>$null
  if ($haveVer -ne $wantVer) { $recreate = $true }
} else {
  $recreate = $true
}

if ($recreate) {
  if (Test-Path ".venv") {
    Write-Host "   recreating .venv (Python version changed or venv missing)"
    Remove-Item -Recurse -Force ".venv"
  }
  & $py -m venv .venv
  Write-Host "   created services/core-api/.venv"
}

& $venvPy -m pip install --upgrade pip wheel
Write-Host "   pip install -r requirements-dev.txt"
& $venvPy -m pip install -r requirements-dev.txt
if ($Full) {
  Write-Host "   pip install -r requirements-optional.txt"
  & $venvPy -m pip install -r requirements-optional.txt
}
Write-Host "   backend dependencies installed"
Pop-Location

Write-Host ""
Write-Host "-> Frontends (apps/*)"
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) { Write-Error "Node.js 18+ not found. Install from https://nodejs.org/ and re-run." }
$nodeVer = node --version
$nodeMajor = [int]($nodeVer -replace '^v','' -split '\.')[0]
if ($nodeMajor -lt 18) { Write-Error "Node $nodeVer is too old (need 18+)." }

$pnpm = Get-Command pnpm -ErrorAction SilentlyContinue
if (-not $pnpm) {
  $corepack = Get-Command corepack -ErrorAction SilentlyContinue
  if ($corepack) {
    Write-Host "   enabling pnpm via corepack"
    corepack enable 2>$null
    corepack prepare pnpm@9.0.0 --activate 2>$null
    $pnpm = Get-Command pnpm -ErrorAction SilentlyContinue
  }
}
if (-not $pnpm) {
  Write-Error "pnpm not found. Install: npm install -g pnpm"
}
pnpm install
Write-Host "   workspace dependencies installed (pnpm)"

Write-Host ""
Write-Host "Bootstrap complete."
Write-Host "  Next: scripts\run-dev.ps1 all   (or: api | desktop | remote)"
if (-not $Full) {
  Write-Host ""
  Write-Host "  Optional ML/scheduler deps were skipped (lite mode default)."
  Write-Host "  To install them later: scripts\bootstrap.ps1 -Full"
}
