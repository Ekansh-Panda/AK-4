# ============================================================================
# Miori Core - one-command install (Windows / PowerShell)
# Runs bootstrap + db init. Safe to re-run.
#
# Usage:
#   scripts\install.ps1
#   scripts\install.ps1 -Full
# ============================================================================
param(
  [switch]$Full
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")

Write-Host "-> Miori Core install"
Write-Host "   repo: $Root"
Write-Host ""

if ($Full) {
  & (Join-Path $PSScriptRoot "bootstrap.ps1") -Full
} else {
  & (Join-Path $PSScriptRoot "bootstrap.ps1")
}

Write-Host ""
Write-Host "-> Database"
& (Join-Path $PSScriptRoot "db-init.ps1")

Write-Host ""
Write-Host "Install complete."
Write-Host ""
Write-Host "  Start everything:"
Write-Host "    scripts\run-dev.ps1 all"
Write-Host ""
Write-Host "  Then open:"
Write-Host "    Desktop UI:  http://localhost:1420"
Write-Host "    API docs:    http://127.0.0.1:8000/docs"
Write-Host "    Remote UI:   http://localhost:5174"
