# ============================================================================
# Miori Core - initialize the SQLite database (Windows / PowerShell)
# Runs the backend's own init_db() so tables (and additive columns) are created
# without starting the server. Prints the resulting DB path.
# ============================================================================
$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$ApiDir = Join-Path $Root "services/core-api"

Write-Host "-> Miori Core database init"

$venvPy = Join-Path $ApiDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
  Write-Host "   [x] backend venv not found at services/core-api/.venv"
  Write-Host "       Install first:  scripts\install.ps1   (or: scripts\bootstrap.ps1)"
  exit 1
}

Set-Location $ApiDir

Write-Host "   -> creating tables via app.db.session.init_db() ..."

$pyScript = @'
from app.db.session import init_db
from app.core.config import settings

init_db()
print("  database initialized")
print("    DATABASE_URL =", settings.DATABASE_URL)

url = settings.DATABASE_URL
if url.startswith("sqlite:///"):
    import os
    path = url[len("sqlite:///"):]
    print("    DB file      =", os.path.abspath(path))
'@

& $venvPy -c $pyScript

Write-Host "[ok] Done."
