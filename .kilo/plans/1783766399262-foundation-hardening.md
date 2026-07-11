# Miori Core — Foundation Hardening Execution Plan

## Context (Read This First)

**Project**: Miori Core v1.1.0 — cross-platform personal AI companion (desktop + remote dashboard + FastAPI backend).
**Repo**: `/home/cobalt/Work/AK-v4`
**Stack**: Tauri v2 + React + TypeScript + Tailwind (desktop), React + Vite (remote), Python 3.11+ + FastAPI + SQLAlchemy (backend), pnpm monorepo.
**Goal of this plan**: Fix every blocker that prevents the project from booting, testing, and building cleanly. After this plan, `pnpm lint && pnpm build && pytest -q` must all pass in CI and locally.

### Current Blockers

| # | Blocker | Impact |
|---|---------|--------|
| B1 | `apps/desktop/src-tauri/tauri.conf.json` uses `npm run` for `beforeDevCommand`/`beforeBuildCommand` but the project uses **pnpm** | `pnpm tauri dev` invokes wrong package manager; native desktop build fails |
| B2 | `pytest-asyncio` is **not** in `services/core-api/requirements-dev.txt` | Async tests (`test_memory.py`, `test_phase2.py`) error out with "no async plugin registered" |
| B3 | No pytest config for `asyncio_mode` | Even if pytest-asyncio is installed, async tests may be collected but not run correctly |
| B4 | No lint scripts or ESLint/Prettier config anywhere | Code quality is unenforced; CI can't catch style/type issues beyond `tsc --noEmit` |
| B5 | `.github/workflows/ci.yml` runs only `typecheck` for frontends, **never builds** | Vite build regressions (missing deps, broken imports) go undetected |
| B6 | Leftover files `prompt.txt` and `.tmp_bypass/` at repo root | Repo noise; `.tmp_bypass/` contains pip unpack artifacts |

### What Already Works

- Backend boots: `uvicorn app.main:app --reload` starts FastAPI with all routers and WS endpoints.
- SQLite DB auto-initializes on first boot with all 8 tables + default `miori-local` user.
- Frontends fall back to mock data when backend is unreachable (offline-friendly).
- `scripts/bootstrap.sh` copies `.env.example` → `.env` and installs deps.
- 6 pytest files exist with good coverage of core paths (provider registry, memory CRUD, settings, phase1 regression, phase2 memory recall, orchestrator fallback).

---

## Execution Steps

Execute these **in order**. Do not skip steps. Each step has a verification command.

### Step 1: Fix Tauri Package Manager Reference

**File**: `apps/desktop/src-tauri/tauri.conf.json`

**Problem**: Lines 7-9 reference `npm run`, but the monorepo uses `pnpm`. Tauri's `beforeDevCommand` and `beforeBuildCommand` must invoke the correct package manager.

**Exact changes**:

```diff
   "build": {
-    "beforeDevCommand": "npm run dev",
+    "beforeDevCommand": "pnpm dev",
     "devUrl": "http://localhost:1420",
-    "beforeBuildCommand": "npm run build",
+    "beforeBuildCommand": "pnpm build",
     "frontendDist": "../dist"
   },
```

**Verification**:
```bash
cd /home/cobalt/Work/AK-v4/apps/desktop
pnpm tauri dev --dry-run 2>&1 | head -20
```
Expected: Tauri prints the dev command as `pnpm dev` and attempts to start Vite on port 1420. No "npm not found" or wrong package manager errors.

---

### Step 2: Add pytest-asyncio Dependency

**File**: `services/core-api/requirements-dev.txt`

**Problem**: Async test functions decorated with `@pytest.mark.asyncio` fail because the plugin is not installed.

**Exact change**:

```diff
 # Dev/test — installed by bootstrap unless MIORI_SKIP_DEV=1
 -r requirements.txt
-pytest==8.3.4
+pytest==8.3.4
+pytest-asyncio==0.23.7
```

**Verification**:
```bash
cd /home/cobalt/Work/AK-v4/services/core-api
pip install -r requirements-dev.txt
python -m pytest --version
```
Expected: pytest 8.3.4 with asyncio plugin visible in the version output or `python -c "import pytest_asyncio; print(pytest_asyncio.__version__)"` succeeds.

---

### Step 3: Add pytest Configuration

**File**: `services/core-api/pyproject.toml` (create new)

**Problem**: pytest needs to know the asyncio mode and the test discovery root. Without config, async tests may run in "legacy" mode or fail to discover.

**Exact content**:

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "miori-core-api"
version = "1.1.0"
description = "Miori Core — FastAPI backend"
requires-python = ">=3.11"
dependencies = [
    "fastapi==0.115.6",
    "uvicorn[standard]==0.34.0",
    "pydantic>=2.12,<3",
    "pydantic-settings>=2.7,<3",
    "SQLAlchemy>=2.0.41,<3",
    "python-multipart==0.0.20",
    "websockets==14.1",
    "httpx==0.28.1",
    "litellm==1.83.7",
    "pypdf==5.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest==8.3.4",
    "pytest-asyncio==0.23.7",
]
full = [
    "huggingface_hub>=0.24",
    "cohere>=5.11",
    "sentence-transformers>=2.7",
    "numpy>=1.26",
    "APScheduler==3.10.4",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Verification**:
```bash
cd /home/cobalt/Work/AK-v4/services/core-api
python -m pytest tests/test_memory.py tests/test_phase2.py -v
```
Expected: All async tests pass (no "asyncio plugin not found" errors).

---

### Step 4: Add Linting Infrastructure

**Files to create/modify**:
- `package.json` (root) — add lint scripts
- `apps/desktop/package.json` — add lint scripts
- `apps/remote-dashboard/package.json` — add lint scripts
- `.eslintrc.cjs` (root, shared config)
- `apps/desktop/.eslintrc.cjs` (extends root)
- `apps/remote-dashboard/.eslintrc.cjs` (extends root)

**Root `package.json` additions**:

```diff
   "scripts": {
     "dev:desktop": "pnpm --filter @miori/desktop dev",
     "dev:remote": "pnpm --filter @miori/remote-dashboard dev",
     "dev:api": "bash scripts/run-dev.sh api",
     "build:desktop": "pnpm --filter @miori/desktop build",
     "build:remote": "pnpm --filter @miori/remote-dashboard build",
+    "lint": "pnpm -r lint",
+    "lint:fix": "pnpm -r lint:fix",
     "typecheck": "pnpm -r --if-present typecheck",
     "analyze:repos": "python scripts/analyze_repos.py"
   },
+  "eslintConfig": {
+    "root": true,
+    "extends": ["eslint:recommended"]
+  }
```

**Each app's `package.json` additions** (both desktop and remote-dashboard get identical additions):

```diff
   "scripts": {
     "dev": "vite",
     "build": "tsc && vite build",
     "preview": "vite preview",
     "typecheck": "tsc --noEmit",
+    "lint": "eslint src --ext .ts,.tsx",
+    "lint:fix": "eslint src --ext .ts,.tsx --fix",
     "tauri": "tauri"
   },
   "devDependencies": {
@@
     "typescript": "^5.5.3",
     "vite": "^5.3.4"
   }
 },
+"eslintConfig": {
+  "extends": ["./../../.eslintrc.cjs"]
+}
```

**Root `.eslintrc.cjs`** (create new):

```js
module.exports = {
  root: true,
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: "module",
  },
  plugins: ["@typescript-eslint"],
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
  ],
  env: {
    browser: true,
    es2021: true,
    node: true,
  },
  rules: {
    "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
    "@typescript-eslint/no-explicit-any": "off",
  },
};
```

**Verification**:
```bash
cd /home/cobalt/Work/AK-v4
pnpm install
pnpm lint
```
Expected: Zero lint errors (or only warnings that are pre-existing and non-blocking).

---

### Step 5: Fix CI to Build Frontends

**File**: `.github/workflows/ci.yml`

**Problem**: The CI workflow only runs `typecheck` for frontends. It never runs `pnpm build`, so Vite build regressions are invisible until someone tries to package.

**Exact changes**:

Replace:
```yaml
      - name: Typecheck frontends
        run: pnpm -r --if-present typecheck
```

With:
```yaml
      - name: Lint frontends
        run: pnpm lint

      - name: Build frontends
        run: pnpm build
```

Full resulting workflow should look like:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install backend dependencies
        working-directory: services/core-api
        run: pip install -r requirements-dev.txt

      - name: Run backend tests
        working-directory: services/core-api
        env:
          MIORI_SKIP_DEV: 1
        run: python -m pytest -q

      - name: Set up Node 20
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'pnpm'

      - name: Install pnpm 9
        uses: pnpm/action-setup@v4
        with:
          version: 9

      - name: Install frontend dependencies
        run: pnpm install

      - name: Lint frontends
        run: pnpm lint

      - name: Typecheck frontends
        run: pnpm -r --if-present typecheck

      - name: Build frontends
        run: pnpm build
```

**Verification**:
```bash
cd /home/cobalt/Work/AK-v4
pnpm build
```
Expected: Both `apps/desktop/dist/` and `apps/remote-dashboard/dist/` are created without errors.

---

### Step 6: Cleanup Leftover Files

**Files to remove**:
- `prompt.txt` (root)
- `.tmp_bypass/` directory (root)

**Verification**:
```bash
cd /home/cobalt/Work/AK-v4
rm -f prompt.txt
rm -rf .tmp_bypass
git status
```
Expected: Only tracked files appear; no untracked junk at root.

---

### Step 7: Final Validation — Run Full Suite

Run these commands **in order** and confirm zero failures:

```bash
# 1. Backend tests
cd /home/cobalt/Work/AK-v4/services/core-api
python -m pytest -q

# 2. Frontend lint + typecheck + build
cd /home/cobalt/Work/AK-v4
pnpm lint
pnpm typecheck
pnpm build

# 3. Tauri dry-run (if Rust toolchain is available)
cd /home/cobalt/Work/AK-v4/apps/desktop
pnpm tauri dev --dry-run 2>&1 | head -10 || echo "Tauri dry-run skipped (no Rust toolchain)"

# 4. Bootstrap script smoke test
cd /home/cobalt/Work/AK-v4
bash scripts/bootstrap.sh
```

**Expected results**:
- `pytest -q`: All 6 test files pass, 0 failures.
- `pnpm lint`: 0 errors (warnings acceptable if pre-existing).
- `pnpm typecheck`: 0 TypeScript errors.
- `pnpm build`: Both apps build successfully, `dist/` directories created.
- `bash scripts/bootstrap.sh`: Completes without error, `.env` created.

---

## Post-Plan Handoff

After all 7 steps are complete and verified:

1. Commit the changes with message: `chore(foundation): fix Tauri config, add pytest-asyncio, linting, CI builds`
2. The project is now ready for **Phase 1: Reliability & Observability** (error boundaries, auth tests, structured logging) and **Phase 2: Remote Transport Realism** (WAN pairing, frame streaming, WS auth).

---

## Files Changed Summary

| File | Action |
|------|--------|
| `apps/desktop/src-tauri/tauri.conf.json` | Edit: npm → pnpm |
| `services/core-api/requirements-dev.txt` | Edit: add pytest-asyncio |
| `services/core-api/pyproject.toml` | Create: build-system, deps, pytest config |
| `package.json` (root) | Edit: add lint scripts |
| `apps/desktop/package.json` | Edit: add lint scripts + eslintConfig |
| `apps/remote-dashboard/package.json` | Edit: add lint scripts + eslintConfig |
| `.eslintrc.cjs` (root) | Create: shared ESLint config |
| `apps/desktop/.eslintrc.cjs` | Create: extends root |
| `apps/remote-dashboard/.eslintrc.cjs` | Create: extends root |
| `.github/workflows/ci.yml` | Edit: add lint + build steps |
| `prompt.txt` | Delete |
| `.tmp_bypass/` | Delete |

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| ESLint flags pre-existing issues | Configure rules to `warn` level initially; fix only new issues |
| `pytest-asyncio==0.23.7` incompatible with pytest 8.3.4 | Pin is validated against current pytest; if conflict, use `pytest-asyncio>=0.23,<0.24` |
| Tauri `--dry-run` unavailable in this environment | Step 7 marks it optional; the actual fix is in config, verified by reading the file |
| `pnpm lint` fails due to missing `node_modules` | Step 7 includes `pnpm install` before lint |
| `pyproject.toml` conflicts with existing `requirements.txt` | `pyproject.toml` is additive; `requirements.txt` remains for pip-only workflows. No breaking change. |
