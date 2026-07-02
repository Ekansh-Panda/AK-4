#!/usr/bin/env bash
# Shared bootstrap helpers (sourced by bootstrap.sh / install.sh).
# shellcheck shell=bash disable=SC2034

bootstrap_repo_root() {
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[1]}")/.." && pwd)"
  printf '%s' "$here"
}

# Prefer a Python with prebuilt wheels (3.11–3.13). Fall back to python3.
bootstrap_find_python() {
  local candidate ver major minor
  for candidate in python3.13 python3.12 python3.11 python3 python; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    ver="$("$candidate" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)" || continue
    major="${ver%%.*}"
    minor="${ver#*.}"
    if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 11 ]; }; then
      continue
    fi
    printf '%s' "$candidate"
    return 0
  done
  return 1
}

bootstrap_python_ok() {
  local py="$1"
  "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null
}

bootstrap_python_version() {
  local py="$1"
  "$py" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>/dev/null
}

bootstrap_python_warn_if_bleeding_edge() {
  local py="$1"
  if "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 14) else 1)' 2>/dev/null; then
    echo "  ! Python 3.14+ detected — using latest pydantic wheels; 3.11–3.13 is the most tested range." >&2
  fi
}

# Use repo-local cache/tmp so home-dir quotas and read-only /tmp don't break pip.
bootstrap_pip_env() {
  local root="$1"
  export PIP_DISABLE_PIP_VERSION_CHECK=1
  export PIP_DEFAULT_TIMEOUT="${PIP_DEFAULT_TIMEOUT:-120}"
  export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$root/.cache/pip}"
  export TMPDIR="${TMPDIR:-$root/.cache/tmp}"
  mkdir -p "$PIP_CACHE_DIR" "$TMPDIR"
}

bootstrap_copy_env_if_missing() {
  local root="$1"
  if [ ! -f "$root/.env" ] && [ -f "$root/.env.example" ]; then
    cp "$root/.env.example" "$root/.env"
    echo "  ✓ created .env from .env.example"
  fi
  if [ ! -f "$root/services/core-api/.env" ] && [ -f "$root/services/core-api/.env.example" ]; then
    cp "$root/services/core-api/.env.example" "$root/services/core-api/.env"
    echo "  ✓ created services/core-api/.env from .env.example"
  fi
}

bootstrap_venv_needs_recreate() {
  local venv_py="$1" want_py="$2"
  [ ! -x "$venv_py" ] && return 0
  local venv_ver want_ver
  venv_ver="$("$venv_py" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>/dev/null)" || return 0
  want_ver="$(bootstrap_python_version "$want_py")" || return 0
  [ "$venv_ver" != "$want_ver" ]
}

bootstrap_install_backend() {
  local root="$1" full="${2:-0}"
  local py req_files=()
  py="$(bootstrap_find_python)" || {
    echo "  ✗ Python 3.11+ not found. Install it and re-run." >&2
    echo "    Arch: sudo pacman -S python python-pip   (or python313 from extra if available)" >&2
    return 1
  }
  bootstrap_python_ok "$py" || {
    echo "  ✗ $py is too old (need 3.11+)." >&2
    return 1
  }

  echo "  using $(bootstrap_python_version "$py") ($py)"
  bootstrap_python_warn_if_bleeding_edge "$py"
  bootstrap_pip_env "$root"

  pushd "$root/services/core-api" >/dev/null
  local venv_py=".venv/bin/python"
  if bootstrap_venv_needs_recreate "$venv_py" "$py"; then
    if [ -d ".venv" ]; then
      echo "  → recreating .venv (Python version changed or venv corrupt)"
      rm -rf .venv
    fi
    "$py" -m venv .venv
    echo "  ✓ created services/core-api/.venv"
  fi

  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m pip install --upgrade pip wheel
  req_files=(requirements-dev.txt)
  if [ "$full" = "1" ]; then
    req_files+=(requirements-optional.txt)
  fi
  for req in "${req_files[@]}"; do
    echo "  → pip install -r $req"
    if ! python -m pip install -r "$req"; then
      echo "  ✗ pip install failed for $req" >&2
      deactivate
      popd >/dev/null
      return 1
    fi
  done
  deactivate
  popd >/dev/null
  echo "  ✓ backend dependencies installed"
}

bootstrap_install_frontend() {
  local root="$1"
  if ! command -v node >/dev/null 2>&1; then
    echo "  ✗ Node.js 18+ not found. Install Node and re-run." >&2
    return 1
  fi
  local nodemajor
  nodemajor="$(node --version 2>/dev/null | sed 's/^v//' | cut -d. -f1)"
  if [ "${nodemajor:-0}" -lt 18 ] 2>/dev/null; then
    echo "  ✗ Node $(node --version) is too old (need 18+)." >&2
    return 1
  fi

  if ! command -v pnpm >/dev/null 2>&1; then
    if command -v corepack >/dev/null 2>&1; then
      echo "  → enabling pnpm via corepack"
      corepack enable >/dev/null 2>&1 || true
      corepack prepare pnpm@9.0.0 --activate >/dev/null 2>&1 || true
    fi
  fi
  if ! command -v pnpm >/dev/null 2>&1; then
    echo "  ✗ pnpm not found." >&2
    echo "    Install: npm install -g pnpm   or   corepack enable && corepack prepare pnpm@9 --activate" >&2
    return 1
  fi

  pushd "$root" >/dev/null
  pnpm install
  popd >/dev/null
  echo "  ✓ workspace dependencies installed (pnpm)"
}

bootstrap_arch_hint() {
  if [ -f /etc/arch-release ] && command -v pacman >/dev/null 2>&1; then
    echo ""
    echo "→ Arch Linux detected"
    echo "  System packages (run once, for Tauri native builds):"
    echo "    sudo pacman -S --needed base-devel curl wget file openssl git nodejs npm python python-pip \\"
    echo "      webkit2gtk-4.1 gtk3 libappindicator-gtk3 librsvg"
    echo "  Web-only dev (no Rust): skip the webkit/gtk line above."
  fi
}
