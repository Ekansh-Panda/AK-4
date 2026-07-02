#!/usr/bin/env bash
# ============================================================================
# Miori Core — dev runner (macOS / Linux)
# Usage: scripts/run-dev.sh [api|desktop|remote|all]
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
TARGET="${1:-all}"

run_api() {
  echo "→ core-api on http://127.0.0.1:8000"
  cd "$ROOT/services/core-api"
  if [ -d ".venv" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
  fi
  exec uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
}

run_desktop() {
  echo "→ desktop (Vite) on http://localhost:1420"
  cd "$ROOT/apps/desktop"
  exec pnpm dev
}

run_remote() {
  echo "→ remote-dashboard (Vite) on http://localhost:5174"
  cd "$ROOT/apps/remote-dashboard"
  exec pnpm dev
}

case "$TARGET" in
  api)     run_api ;;
  desktop) run_desktop ;;
  remote)  run_remote ;;
  all)
    echo "→ Starting api + desktop + remote together (Ctrl-C stops all)."
    ( run_api )     &
    ( run_desktop ) &
    ( run_remote )  &
    wait
    ;;
  *)
    echo "Usage: scripts/run-dev.sh [api|desktop|remote|all]" >&2
    exit 1
    ;;
esac
