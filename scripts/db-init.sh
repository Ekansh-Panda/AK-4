#!/usr/bin/env bash
# ============================================================================
# Miori Core — initialize the SQLite database (macOS / Linux)
# Runs the backend's own init_db() so tables (and additive columns) are created
# without starting the server. Prints the resulting DB path.
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT/services/core-api"

echo "→ Miori Core database init"

if [ ! -d "$API_DIR/.venv" ]; then
  echo "  ✗ backend venv not found at services/core-api/.venv" >&2
  echo "    Install first:  bash scripts/install.sh   (or: bash scripts/bootstrap.sh)" >&2
  exit 1
fi

cd "$API_DIR"
# shellcheck disable=SC1091
source .venv/bin/activate

echo "  → creating tables via app.db.session.init_db() …"
python - <<'PY'
from app.db.session import init_db
from app.core.config import settings

init_db()
print("  ✓ database initialized")
print("    DATABASE_URL =", settings.DATABASE_URL)

# For the default sqlite:///./relative URL, show the on-disk path.
url = settings.DATABASE_URL
if url.startswith("sqlite:///"):
    import os
    path = url[len("sqlite:///"):]
    print("    DB file      =", os.path.abspath(path))
PY

deactivate
echo "✓ Done."
