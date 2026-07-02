#!/usr/bin/env bash
# ============================================================================
# Miori Core — bootstrap (macOS / Linux)
# Sets up env files, Python venv, and frontend deps.
#
# Usage:
#   bash scripts/bootstrap.sh           # core + dev deps (recommended)
#   bash scripts/bootstrap.sh --full    # also install ML/scheduler optional deps
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/bootstrap-common.sh
source "$ROOT/scripts/lib/bootstrap-common.sh"

FULL=0
for arg in "$@"; do
  case "$arg" in
    --full) FULL=1 ;;
    -h|--help)
      echo "Usage: bash scripts/bootstrap.sh [--full]"
      echo "  --full  Install optional heavy deps (sentence-transformers, etc.)"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg (try --help)" >&2
      exit 1
      ;;
  esac
done

cd "$ROOT"
echo "→ Miori Core bootstrap"
echo "  repo: $ROOT"

echo ""
echo "→ Configuration"
bootstrap_copy_env_if_missing "$ROOT"

echo ""
echo "→ Backend (services/core-api)"
bootstrap_install_backend "$ROOT" "$FULL"

echo ""
echo "→ Frontends (apps/*)"
bootstrap_install_frontend "$ROOT"

bootstrap_arch_hint

echo ""
echo "✓ Bootstrap complete."
echo "  Next:"
echo "    bash scripts/run-dev.sh all     # api + desktop + remote"
echo "    bash scripts/run-dev.sh api     # backend only"
if [ "$FULL" = "0" ]; then
  echo ""
  echo "  Optional ML/scheduler deps were skipped (lite mode default)."
  echo "  To install them later: bash scripts/bootstrap.sh --full"
fi
