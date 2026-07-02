# ============================================================================
# Miori Core - dev runner (Windows / PowerShell)
# Usage: scripts\run-dev.ps1 [api|desktop|remote|all]
# ============================================================================
param([string]$Target = "all")
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")

function Run-Api {
  Write-Host "-> core-api on http://127.0.0.1:8000"
  Set-Location (Join-Path $Root "services/core-api")
  if (Test-Path ".venv\Scripts\Activate.ps1") { . .\.venv\Scripts\Activate.ps1 }
  uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
}
function Run-Desktop {
  Write-Host "-> desktop (Vite) on http://localhost:1420"
  Set-Location (Join-Path $Root "apps/desktop"); pnpm dev
}
function Run-Remote {
  Write-Host "-> remote-dashboard (Vite) on http://localhost:5174"
  Set-Location (Join-Path $Root "apps/remote-dashboard"); pnpm dev
}

switch ($Target) {
  "api"     { Run-Api }
  "desktop" { Run-Desktop }
  "remote"  { Run-Remote }
  "all" {
    Write-Host "-> Starting api + desktop + remote in separate windows."
    Start-Process powershell -ArgumentList "-NoExit","-Command","& '$PSCommandPath' api"
    Start-Process powershell -ArgumentList "-NoExit","-Command","& '$PSCommandPath' desktop"
    Start-Process powershell -ArgumentList "-NoExit","-Command","& '$PSCommandPath' remote"
  }
  default { Write-Error "Usage: scripts\run-dev.ps1 [api|desktop|remote|all]"; exit 1 }
}
