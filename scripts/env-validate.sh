#!/usr/bin/env bash
# ============================================================================
# Miori Core — environment validator (macOS / Linux)
# Checks toolchain versions, .env presence, and which provider keys are set.
# Exits non-zero ONLY when Python 3.11+ or Node 18+ is missing.
# ============================================================================
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0

echo "→ Miori Core environment check"
echo "  repo: $ROOT"
echo ""

# ---- Python 3.11+ --------------------------------------------------------
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  PY=""
fi

if [ -n "$PY" ]; then
  PYVER="$("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)"
  if "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    echo "  ✓ Python $PYVER  ($PY)"
    if "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 14) else 1)' 2>/dev/null; then
      echo "  ! Python 3.14+ — supported, but 3.11–3.13 is the most tested range."
    fi
  else
    echo "  ✗ Python $PYVER found, but 3.11+ is required" >&2
    FAIL=1
  fi
else
  echo "  ✗ Python not found (need 3.11+)" >&2
  FAIL=1
fi

# ---- Node 18+ ------------------------------------------------------------
if command -v node >/dev/null 2>&1; then
  NODEVER="$(node --version 2>/dev/null)"           # e.g. v18.19.0
  NODEMAJOR="$(echo "$NODEVER" | sed 's/^v//' | cut -d. -f1)"
  if [ "${NODEMAJOR:-0}" -ge 18 ] 2>/dev/null; then
    echo "  ✓ Node $NODEVER"
  else
    echo "  ✗ Node $NODEVER found, but 18+ is required" >&2
    FAIL=1
  fi
else
  echo "  ✗ Node not found (need 18+)" >&2
  FAIL=1
fi

# ---- pnpm (warn only) ----------------------------------------------------
if command -v pnpm >/dev/null 2>&1; then
  echo "  ✓ pnpm $(pnpm --version 2>/dev/null)"
else
  echo "  ! pnpm not found — install with: npm install -g pnpm"
fi

# ---- .env presence (warn only) -------------------------------------------
echo ""
echo "→ Configuration"
API_ENV="services/core-api/.env"
ROOT_ENV=".env"
if [ -f "$API_ENV" ]; then
  echo "  ✓ $API_ENV present"
elif [ -f "$ROOT_ENV" ]; then
  echo "  ✓ $ROOT_ENV present ($API_ENV not found — backend defaults will be used)"
else
  echo "  ! no .env found — copy templates:"
  echo "      cp .env.example .env"
  echo "      cp services/core-api/.env.example services/core-api/.env"
fi

# ---- Provider keys (masked) ----------------------------------------------
# Read from the backend .env (falling back to root .env), then env vars.
mask() {
  # $1 = value; print a masked form (first 4 + last 4 chars) or **** if short.
  v="$1"
  n=${#v}
  if [ "$n" -le 8 ]; then
    printf '****'
  else
    first="$(printf '%s' "$v" | cut -c1-4)"
    last="$(printf '%s' "$v" | rev | cut -c1-4 | rev)"
    printf '%s…%s' "$first" "$last"
  fi
}

read_key() {
  # $1 = key name. Prefer process env, else grep the .env files.
  name="$1"
  val="$(printenv "$name" 2>/dev/null || true)"
  if [ -z "$val" ]; then
    for f in "$API_ENV" "$ROOT_ENV"; do
      [ -f "$f" ] || continue
      line="$(grep -E "^[[:space:]]*${name}=" "$f" 2>/dev/null | tail -n1)"
      if [ -n "$line" ]; then
        val="${line#*=}"
        break
      fi
    done
  fi
  printf '%s' "$val"
}

echo ""
echo "→ Provider keys"
for KEY in OPENAI_API_KEY OPENAI_BASE_URL OPENAI_MODEL GEMINI_API_KEY GOOGLE_API_KEY GEMINI_MODEL; do
  VAL="$(read_key "$KEY")"
  case "$KEY" in
    *_KEY)
      if [ -n "$VAL" ]; then echo "  ✓ $KEY = $(mask "$VAL")"; else echo "  · $KEY = (not set)"; fi
      ;;
    *)
      if [ -n "$VAL" ]; then echo "  · $KEY = $VAL"; else echo "  · $KEY = (default)"; fi
      ;;
  esac
done
echo "  (no keys set is fine — the mock provider works offline)"

echo ""
if [ "$FAIL" -ne 0 ]; then
  echo "✗ Environment check failed — install the missing required tools above." >&2
  exit 1
fi
echo "✓ Environment looks good."
