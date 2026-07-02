#!/usr/bin/env bash
# ============================================================================
# Miori Core — one-command install (macOS / Linux)
# Runs bootstrap + db init. Safe to re-run.
#
# Usage:
#   bash scripts/install.sh
#   bash scripts/install.sh --full
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "→ Miori Core install"
echo "  repo: $ROOT"
echo ""

bash "$ROOT/scripts/bootstrap.sh" "$@"

echo ""
echo "→ Database"
bash "$ROOT/scripts/db-init.sh"

echo ""
echo "✓ Install complete."
echo ""
echo "  Start everything:"
echo "    bash scripts/run-dev.sh all"
echo ""
echo "  Then open:"
echo "    Desktop UI:  http://localhost:1420"
echo "    API docs:    http://127.0.0.1:8000/docs"
echo "    Remote UI:   http://localhost:5174"
