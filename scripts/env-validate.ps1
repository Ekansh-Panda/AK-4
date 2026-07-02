# ============================================================================
# Miori Core - environment validator (Windows / PowerShell)
# Checks toolchain versions, .env presence, and which provider keys are set.
# Exits non-zero ONLY when Python 3.11+ or Node 18+ is missing.
# ============================================================================
$ErrorActionPreference = "Continue"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$fail = 0

Write-Host "-> Miori Core environment check"
Write-Host "   repo: $Root"
Write-Host ""

# ---- Python 3.11+ --------------------------------------------------------
$py = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $py) { $py = (Get-Command python3 -ErrorAction SilentlyContinue) }
if ($py) {
  $pyver = (& $py.Source -c "import sys; print('%d.%d' % sys.version_info[:2])") 2>$null
  & $py.Source -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" 2>$null
  if ($LASTEXITCODE -eq 0) {
    Write-Host "   [ok] Python $pyver  ($($py.Source))"
  } else {
    Write-Host "   [x]  Python $pyver found, but 3.11+ is required"
    $fail = 1
  }
} else {
  Write-Host "   [x]  Python not found (need 3.11+)"
  $fail = 1
}

# ---- Node 18+ ------------------------------------------------------------
$node = (Get-Command node -ErrorAction SilentlyContinue)
if ($node) {
  $nodever = (node --version) 2>$null          # e.g. v18.19.0
  $nodemajor = [int]($nodever -replace '^v','' -split '\.')[0]
  if ($nodemajor -ge 18) {
    Write-Host "   [ok] Node $nodever"
  } else {
    Write-Host "   [x]  Node $nodever found, but 18+ is required"
    $fail = 1
  }
} else {
  Write-Host "   [x]  Node not found (need 18+)"
  $fail = 1
}

# ---- pnpm (warn only) ----------------------------------------------------
$pnpm = (Get-Command pnpm -ErrorAction SilentlyContinue)
if ($pnpm) {
  Write-Host "   [ok] pnpm $(pnpm --version)"
} else {
  Write-Host "   [!]  pnpm not found - install with: npm install -g pnpm"
}

# ---- .env presence (warn only) -------------------------------------------
Write-Host ""
Write-Host "-> Configuration"
$apiEnv = "services/core-api/.env"
$rootEnv = ".env"
if (Test-Path $apiEnv) {
  Write-Host "   [ok] $apiEnv present"
} elseif (Test-Path $rootEnv) {
  Write-Host "   [ok] $rootEnv present ($apiEnv not found - backend defaults will be used)"
} else {
  Write-Host "   [!]  no .env found - copy templates:"
  Write-Host "          Copy-Item .env.example .env"
  Write-Host "          Copy-Item services/core-api/.env.example services/core-api/.env"
}

# ---- Provider keys (masked) ----------------------------------------------
function Mask([string]$v) {
  if ([string]::IsNullOrEmpty($v)) { return "(not set)" }
  if ($v.Length -le 8) { return "****" }
  return $v.Substring(0,4) + "..." + $v.Substring($v.Length - 4)
}

function Read-Key([string]$name) {
  # Prefer process env, else grep the .env files.
  $val = [Environment]::GetEnvironmentVariable($name)
  if ([string]::IsNullOrEmpty($val)) {
    foreach ($f in @($apiEnv, $rootEnv)) {
      if (Test-Path $f) {
        $line = Select-String -Path $f -Pattern "^\s*$name=" | Select-Object -Last 1
        if ($line) { $val = ($line.Line -replace "^\s*$name=", ""); break }
      }
    }
  }
  return $val
}

Write-Host ""
Write-Host "-> Provider keys"
foreach ($key in @("OPENAI_API_KEY","OPENAI_BASE_URL","OPENAI_MODEL","GEMINI_API_KEY","GOOGLE_API_KEY","GEMINI_MODEL")) {
  $val = Read-Key $key
  if ($key -like "*_KEY") {
    if ([string]::IsNullOrEmpty($val)) { Write-Host "   .  $key = (not set)" }
    else { Write-Host "   [ok] $key = $(Mask $val)" }
  } else {
    if ([string]::IsNullOrEmpty($val)) { Write-Host "   .  $key = (default)" }
    else { Write-Host "   .  $key = $val" }
  }
}
Write-Host "   (no keys set is fine - the mock provider works offline)"

Write-Host ""
if ($fail -ne 0) {
  Write-Host "[x] Environment check failed - install the missing required tools above."
  exit 1
}
Write-Host "[ok] Environment looks good."
