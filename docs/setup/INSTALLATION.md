# Miori Core — Installation & Setup

The complete guide to getting **Miori Core v1** running on your machine: the
FastAPI backend, the Tauri desktop companion, and the mobile remote dashboard.

Miori boots fully offline with a **mock provider** (no API keys required) and
uses **SQLite** by default. Real model providers (OpenAI / OpenAI-compatible /
Gemini), file text ingestion, and persisted settings are all wired in v1 — see
[Provider API key setup](#11-provider-api-key-setup).

> You can run the **web UIs and backend with no Rust toolchain at all**. Rust +
> the Tauri prerequisites are only needed to run/build the *native* desktop
> window (`tauri dev` / `tauri build`).

## Quick install (recommended)

From the repo root, one command sets up `.env` files, the Python venv, frontend
deps, and the SQLite database:

```bash
git clone <repo-url> miori-core
cd miori-core
bash scripts/install.sh          # Windows: scripts\install.ps1
bash scripts/run-dev.sh all        # start api + desktop + remote
```

Then open **http://localhost:1420** (desktop UI) and **http://127.0.0.1:8000/docs**
(API). No API keys needed — the mock provider works offline.

> **Arch Linux / Python 3.14:** the installer uses prebuilt wheels and a
> repo-local pip cache (`.cache/`) so home-directory quotas and `/tmp` limits
> don't break installs. Heavy ML deps are **not** installed by default.

Optional flags:

```bash
bash scripts/install.sh --full     # also install ML/scheduler optional deps
bash scripts/env-validate.sh       # sanity-check your toolchain
```

---

## Table of contents

1. [Overview & prerequisites](#1-overview--prerequisites)
2. [Tauri prerequisites (per OS)](#2-tauri-prerequisites-per-os)
3. [Clone the repo](#3-clone-the-repo)
4. [Configure `.env`](#4-configure-env)
5. [Install dependencies](#5-install-dependencies)
6. [Initialize the database](#6-initialize-the-database)
7. [Run the backend](#7-run-the-backend)
8. [Run the desktop app](#8-run-the-desktop-app)
9. [Run the remote dashboard](#9-run-the-remote-dashboard)
10. [Build production desktop binaries](#10-build-production-desktop-binaries)
11. [Provider API key setup](#11-provider-api-key-setup)
12. [Where data is stored locally](#12-where-data-is-stored-locally)
13. [Low-end / Lite mode notes](#13-low-end--lite-mode-notes)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Overview & prerequisites

Miori Core is a **pnpm-workspace monorepo** for the frontends (`apps/*`,
`packages/*`) plus a **separate Python venv backend** at `services/core-api`.

| Component | Runtime | Dev URL |
| --- | --- | --- |
| `services/core-api` (FastAPI) | Python 3.11+ | http://127.0.0.1:8000 (docs at `/docs`) |
| `apps/desktop` (Tauri + Vite) | Node 18+, pnpm, (Rust for native) | http://localhost:1420 |
| `apps/remote-dashboard` (Vite) | Node 18+, pnpm | http://localhost:5174 (LAN-accessible) |

### Base prerequisites (all OSes)

| Tool | Version | Check | Get it |
| --- | --- | --- | --- |
| Python | 3.11–3.14 | `python3 --version` | https://www.python.org/downloads/ |
| Node.js | 18+ | `node --version` | https://nodejs.org/ |
| pnpm | 9+ | `pnpm --version` | enabled automatically via corepack, or `npm install -g pnpm` |
| Git | any | `git --version` | https://git-scm.com/ |
| Rust + Cargo | stable | `cargo --version` | https://rustup.rs/ *(only for native desktop)* |

> **Python note:** 3.11–3.13 is the most tested range. Arch Linux currently ships
> Python 3.14 — that works with this repo (prebuilt wheels for pydantic/SQLAlchemy).
> If you hit build-from-source errors, install `python313` from Arch Extra and re-run
> `bash scripts/install.sh` (the script recreates the venv with the best Python it finds).

> The repo pins `pnpm@9` (`packageManager` in `package.json`) and `node >=18`.
> A helper, [`scripts/env-validate.sh` / `.ps1`](#5-install-dependencies),
> checks all of the above and reports which provider keys are set.

---

## 2. Tauri prerequisites (per OS)

Only needed to run the **native** desktop window (`pnpm --filter @miori/desktop
tauri dev`) or build installers (`tauri build`). Follow the official guide for
the authoritative list: <https://tauri.app/start/prerequisites/>.

### Linux

Install Rust via [rustup](https://rustup.rs/) plus the WebKitGTK / GTK system
packages.

```bash
# Debian / Ubuntu
sudo apt update
sudo apt install -y \
  libwebkit2gtk-4.1-dev build-essential curl wget file \
  libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev \
  libgtk-3-dev python3 python3-pip python3-venv git nodejs npm

# Fedora
sudo dnf install -y webkit2gtk4.1-devel openssl-devel curl wget file \
  libappindicator-gtk3-devel librsvg2-devel gtk3-devel python3 python3-pip \
  nodejs npm git @"C Development Tools and Libraries"

# Arch Linux — base toolchain (web UI + backend, no native Tauri yet)
sudo pacman -S --needed base-devel curl wget file openssl git nodejs npm \
  python python-pip

# Arch Linux — add these only for native Tauri builds (tauri dev / tauri build)
sudo pacman -S --needed webkit2gtk-4.1 gtk3 libappindicator-gtk3 librsvg
```

### macOS

```bash
xcode-select --install        # Xcode Command Line Tools
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh   # Rust
```

### Windows

1. Install **Microsoft C++ Build Tools** (the "Desktop development with C++"
   workload): <https://visualstudio.microsoft.com/visual-cpp-build-tools/>.
2. Install **WebView2 Runtime** (preinstalled on Windows 11; for Windows 10
   grab the Evergreen installer): <https://developer.microsoft.com/microsoft-edge/webview2/>.
3. Install **Rust** via <https://rustup.rs/> (uses the MSVC toolchain).

---

## 3. Clone the repo

```bash
git clone <repo-url> miori-core
cd miori-core
```

All commands below are run **from the repo root** unless stated otherwise.

---

## 4. Configure `.env`

Miori reads configuration from `.env` files. **`scripts/install.sh` copies the
templates automatically** if they are missing. To configure manually:

**Backend** (`services/core-api/.env`) is the important one — the FastAPI
`Settings` class reads **bare, un-prefixed** names (case-insensitive). The root
`.env` mainly carries the `VITE_*` values the frontends read.

```bash
# bash / macOS / Linux
cp .env.example .env
cp services/core-api/.env.example services/core-api/.env
```

```powershell
# Windows / PowerShell
Copy-Item .env.example .env
Copy-Item services/core-api/.env.example services/core-api/.env
```

### Backend keys (`services/core-api/.env`)

| Key | Default | Meaning |
| --- | --- | --- |
| `APP_NAME` | `Miori Core` | Display name. |
| `APP_VERSION` | `1.1.0` | Reported version. |
| `DEBUG` | `true` | Verbose logging. |
| `HOST` | `127.0.0.1` | Bind address for the API. |
| `PORT` | `8000` | API port. |
| `DATABASE_URL` | `sqlite:///./miori.db` | SQLAlchemy URL. SQLite by default. |
| `CORS_ORIGINS` | localhost dev origins | **Comma-separated** allowed origins. Must include the frontends' URLs (see note below). |
| `REMOTE_ENABLED` | `true` | Enables remote dashboard / device endpoints. Set `false` to lock them off. |
| `LITE_MODE` | `true` | Keeps heavy/optional deps lazy/off. Recommended on for low-end machines. |
| `PROMPTS_DIR` | `../../packages/prompts` | Persona prompt packs. Degrades gracefully if missing. |
| `UPLOAD_DIR` | `./data/uploads` | Where uploaded files are stored. |
| `MAX_UPLOAD_BYTES` | `26214400` (25 MB) | Uploads above this return HTTP 413. |
| `DEFAULT_PROVIDER` | `mock` | Active provider on first boot: `mock` \| `openai` \| `gemini`. |
| `OPENAI_API_KEY` | _(empty)_ | OpenAI / OpenAI-compatible key. |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Point at OpenRouter or a local server to reuse the OpenAI provider. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Default OpenAI model. |
| `GEMINI_API_KEY` | _(empty)_ | Google Gemini key (preferred). |
| `GOOGLE_API_KEY` | _(empty)_ | Accepted as an alias for `GEMINI_API_KEY`. |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Default Gemini model. |

> **CORS note (important):** the desktop dev server runs on **port 1420** and
> the remote dashboard on **5174**. Make sure `CORS_ORIGINS` includes the
> origins you actually use, e.g.:
> ```
> CORS_ORIGINS=http://localhost:1420,http://localhost:5174,http://127.0.0.1:1420,http://127.0.0.1:5174
> ```
> If the desktop UI can't reach the backend in the browser, a missing
> `http://localhost:1420` origin is the usual cause.

### Frontend keys (root `.env`)

| Key | Default | Read by |
| --- | --- | --- |
| `VITE_MIORI_API` | `http://localhost:8000/api` | Desktop REST client (must keep the `/api` suffix). |
| `VITE_MIORI_WS` | `ws://localhost:8000/ws/chat` | Desktop chat WebSocket (full path). |

The remote dashboard reads only `VITE_*` vars; its optional
`apps/remote-dashboard/.env.example` exposes `VITE_DEFAULT_HOST` to pre-fill the
login screen. The desktop app has **no** `.env.example` — the defaults above
work out of the box; create `apps/desktop/.env` only if you need to override.

> **Providers are optional.** With no keys set, Miori uses the `mock` provider
> (echoes your last message) and everything stays demoable offline.

---

## 5. Install dependencies

The fastest path is the **one-command installer** (bootstrap + DB init):

```bash
# bash / macOS / Linux
bash scripts/install.sh
```

```powershell
# Windows / PowerShell
scripts\install.ps1
```

Or bootstrap only (without DB init):

```bash
bash scripts/bootstrap.sh           # core deps only (recommended)
bash scripts/bootstrap.sh --full    # also ML/scheduler optional deps (~GB download)
```

```powershell
scripts\bootstrap.ps1
scripts\bootstrap.ps1 -Full
```

The bootstrap script:

- Picks the best Python 3.11+ on your PATH (prefers 3.13 → 3.12 → 3.11)
- Recreates the venv if the Python version changed
- Uses a **repo-local pip cache** (`.cache/pip`) and temp dir (`.cache/tmp`) so
  home-directory quotas and read-only `/tmp` don't break pip
- Copies `.env` templates if missing
- Enables **pnpm via corepack** when available
- Installs **lightweight core deps only** by default (no torch/sentence-transformers)

Before (or after) install, sanity-check your environment:

```bash
bash scripts/env-validate.sh        # Windows: scripts\env-validate.ps1
```

`env-validate` verifies Python 3.11+ and Node 18+ (exits non-zero if either is
missing), checks that pnpm is present, warns if no `.env` exists, and prints
which provider keys are set (masked).

### Dependency tiers

| File | What it installs | When |
| --- | --- | --- |
| `requirements.txt` | FastAPI, pydantic, SQLAlchemy, httpx, … | Always (default) |
| `requirements-dev.txt` | Above + pytest | Default bootstrap |
| `requirements-optional.txt` | sentence-transformers, numpy, cohere, APScheduler, … | `--full` flag only |

### Manual install (if you prefer)

```bash
# Backend
cd services/core-api
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install --upgrade pip wheel
pip install -r requirements-dev.txt  # or requirements-optional.txt for ML
deactivate
cd ../..

# Frontends (from repo root)
corepack enable && corepack prepare pnpm@9 --activate   # if pnpm missing
pnpm install
```

---

## 6. Initialize the database

The backend **creates the SQLite DB and tables automatically on startup**
(FastAPI lifespan calls `init_db()`), so you usually don't need a manual step —
just [run the backend](#7-run-the-backend). On first boot it creates `miori.db`
and the `data/uploads/` directory and logs the DB path.

To initialize (or repair an existing DB's added columns) **without** starting
the server, use the helper:

```bash
bash scripts/db-init.sh             # Windows: scripts\db-init.ps1
```

This activates the backend venv and runs the backend's own `init_db()`, then
prints the resulting DB path. If the venv is missing it tells you to run
`scripts/bootstrap.sh` first.

Equivalent manual command:

```bash
cd services/core-api
source .venv/bin/activate            # Windows: .venv\Scripts\activate
python -c "from app.db.session import init_db; init_db()"
```

---

## 7. Run the backend

```bash
# via the dev runner (activates the venv for you)
bash scripts/run-dev.sh api          # Windows: scripts\run-dev.ps1 api
```

Manual equivalent:

```bash
cd services/core-api
source .venv/bin/activate            # Windows: .venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API serves on **http://127.0.0.1:8000**. Interactive OpenAPI docs are at
**http://127.0.0.1:8000/docs**, and a health check at
**http://127.0.0.1:8000/api/health**.

---

## 8. Run the desktop app

You have two modes:

**Web mode** (no Rust needed) — runs the UI in your browser:

```bash
pnpm --filter @miori/desktop dev
```

Open **http://localhost:1420**. (The Vite dev server uses a fixed port `1420`.)

**Native mode** (requires the [Tauri prerequisites](#2-tauri-prerequisites-per-os)) —
opens the real desktop window:

```bash
pnpm --filter @miori/desktop tauri dev
```

`tauri dev` starts Vite (on 1420) and then launches the native window pointed at
it. The first native build compiles Rust crates and can take several minutes.

> The frontend falls back to mock data when the backend is unreachable, so the
> shell is usable on its own. Start the backend (step 7) for real chat,
> persistence, and providers.

---

## 9. Run the remote dashboard

```bash
pnpm --filter @miori/remote-dashboard dev
```

Open **http://localhost:5174** on the host machine.

**From your phone (LAN):** the dev server binds to all interfaces
(`server.host = true`), so on a phone on the same network open
`http://<host-lan-ip>:5174` (find the host IP with `ipconfig` on Windows or `ip
addr` / `ifconfig` on Linux/macOS).

For the device / power-control features the dashboard needs the **backend
running with `REMOTE_ENABLED=true`** (the default in
`services/core-api/.env.example`). The dashboard talks to the backend via
`VITE_MIORI_API`; when reaching it from a phone, point that at the host's LAN IP
(e.g. `http://192.168.1.20:8000/api`) and add that origin to `CORS_ORIGINS`.

---

## 10. Build production desktop binaries

Requires the [Tauri prerequisites](#2-tauri-prerequisites-per-os) for your OS.

```bash
pnpm --filter @miori/desktop tauri build
```

This builds the web bundle (`tsc && vite build`) and then produces native
installers/bundles for the current platform under
`apps/desktop/src-tauri/target/release/bundle/` (`.msi`/`.exe` on Windows,
`.dmg`/`.app` on macOS, `.deb`/`.AppImage`/`.rpm` on Linux).

**Icons:** the bundle expects the icons listed in
`apps/desktop/src-tauri/tauri.conf.json`. Regenerate them from a single
1024×1024 source PNG with:

```bash
pnpm --filter @miori/desktop tauri icon path/to/icon.png
```

> You can only build the installer format(s) native to the OS you're on
> (cross-compiling installers is not supported here).

---

## 11. Provider API key setup

Three providers ship in the registry. The **active** provider is read from the
DB at startup (defaulting to `DEFAULT_PROVIDER`, then `mock`) and can be changed
at runtime. If the active provider has no key, chat **transparently falls back
to `mock`** — it never crashes.

| Provider | Key(s) | Notes |
| --- | --- | --- |
| `mock` | — | Always available; echoes your last message. Offline fallback. |
| `openai` | `OPENAI_API_KEY` | OpenAI Chat Completions. Default model `gpt-4o-mini`. |
| `gemini` | `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) | Google Generative Language API. Default model `gemini-1.5-flash`. |

Set keys in `services/core-api/.env`:

```ini
# OpenAI
OPENAI_API_KEY=sk-...

# OpenRouter (reuses the OpenAI provider via a custom base URL)
OPENAI_API_KEY=sk-or-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openai/gpt-4o-mini

# A local OpenAI-compatible server (e.g. Ollama, LM Studio)
OPENAI_API_KEY=not-needed
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=llama3.1

# Gemini
GEMINI_API_KEY=...
```

**Pick the active provider** — in the desktop app's **Settings** page, or via
the API:

```bash
curl -X PUT http://localhost:8000/api/providers/active \
  -H 'content-type: application/json' \
  -d '{"name":"openai"}'
```

Restart the backend after editing `.env` so new keys are picked up.

---

## 12. Where data is stored locally

All paths are relative to `services/core-api/` (the backend's working dir):

| What | Location |
| --- | --- |
| SQLite database | `services/core-api/miori.db` (from `DATABASE_URL=sqlite:///./miori.db`) |
| Uploaded files | `services/core-api/data/uploads/` (from `UPLOAD_DIR`) |

Both are created automatically on first backend boot. To reset Miori's local
state, stop the backend and delete `miori.db` (and optionally `data/uploads/`);
it will be recreated on next start. These paths are git-ignored.

---

## 13. Feature Flags

Miori is designed to scale down gracefully. You can turn off heavy subsystems using these variables in `services/core-api/.env` (or the root `.env`):

- `LITE_MODE=true` (Default: `true`)
  Disables the vector database, heavy embedding models, and remote pairing. It uses raw SQLite substring search instead. Perfect for laptops or Raspberry Pi.
- `REMOTE_ENABLED=true` (Default: `true`)
  Controls whether the dashboard and pairing routes are exposed to the LAN.
- `COMPUTER_USE_ENABLED=false` (Default: `false`)
  Controls whether the LLM is allowed to take screenshots and move the mouse.
- `SCHEDULER_ENABLED=true` (Default: `true`)
  Enables the background task scheduler which automatically checks for and notifies about due tasks.

---

## 14. Troubleshooting

**`bash scripts/install.sh` / bootstrap fails on pip**

Common causes and fixes:

| Symptom | Fix |
| --- | --- |
| `disk quota exceeded` / `No space left on device` | The installer uses `.cache/` inside the repo. Free disk space, then re-run. Optionally: `rm -rf .cache services/core-api/.venv && bash scripts/install.sh` |
| `metadata-generation-failed` for `pydantic-core` | Old pydantic pinned without 3.14 wheels. Delete `.venv`, pull latest, re-run install. Or use Python 3.11–3.13. |
| `TypeError: Union __getitem__` on db-init | SQLAlchemy too old for Python 3.14. Delete `.venv` and re-run install (needs SQLAlchemy ≥ 2.0.41). |
| pip tries to compile Rust crates | You're on an unsupported Python or missing wheels. Use Python 3.11–3.13, or ensure you haven't pinned old pydantic. |
| `Permission denied` on `~/.cache` | Install uses repo-local `.cache/` — re-run from a fresh clone or delete `.cache/`. |

**Arch Linux: `pacman` package not found (`appmenu-gtk-module`, etc.)**

Package names change between Arch releases. Use the commands in
[Tauri prerequisites](#2-tauri-prerequisites-per-os) above — `appmenu-gtk-module`
was removed from the list. For web-only dev you only need `base-devel python
nodejs npm git`.

**`pnpm: command not found`**
Run `corepack enable && corepack prepare pnpm@9 --activate`, or install globally:
`npm install -g pnpm`. Verify with `pnpm --version` (need 9+).

**Port already in use (8000 / 1420 / 5174)**
Something else is bound to the port. Find and stop it, or change the port.
- Backend: `uvicorn app.main:app --port 8001` (and update `VITE_MIORI_API`).
- Desktop Vite uses a **fixed** `1420` (`strictPort: true`) — free the port
  rather than expecting it to auto-increment.
- Find the process: `lsof -i :8000` (macOS/Linux) or
  `netstat -ano | findstr :8000` then `taskkill /PID <pid> /F` (Windows).

**CORS errors in the browser console**
The origin you're loading the UI from isn't in `CORS_ORIGINS`. Add it to
`services/core-api/.env` — most commonly `http://localhost:1420` for the desktop
web UI — then restart the backend. For phone/LAN access add the host's LAN
origin too.

**venv won't activate**
- macOS/Linux: `source services/core-api/.venv/bin/activate`
- Windows PowerShell: `services\core-api\.venv\Scripts\Activate.ps1`
  (if blocked: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)
- Windows cmd: `services\core-api\.venv\Scripts\activate.bat`
- Missing `.venv`? Run `scripts/bootstrap.sh` (or `.ps1`) first.

**Provider key errors / replies look like an echo**
If the active provider's key is missing or invalid, chat silently falls back to
the `mock` provider (which echoes). Confirm the key in
`services/core-api/.env`, restart the backend, and set the active provider
(Settings page or `PUT /api/providers/active`). `scripts/env-validate.sh` shows
which keys are detected.

**Tauri build / `tauri dev` failures**
- Make sure the [Tauri prerequisites](#2-tauri-prerequisites-per-os) for your OS
  are installed and Rust is on `PATH` (`cargo --version`).
- **Windows:** install the "Desktop development with C++" build tools **and** the
  WebView2 Runtime.
- **Linux:** install the WebKitGTK/GTK `-dev` packages (e.g.
  `libwebkit2gtk-4.1-dev`, `libgtk-3-dev`). A "webkit2gtk not found" error means
  these are missing.
- **macOS:** run `xcode-select --install`.
- Clear a corrupt build: delete `apps/desktop/src-tauri/target/` and rebuild.

**Backend imports fail / `ModuleNotFoundError`**
Activate the venv first, then `pip install -r services/core-api/requirements-dev.txt`.
Run `uvicorn`/`python` from inside `services/core-api` so `app.*` resolves.
If the venv was created with a different Python, delete it and re-run
`bash scripts/install.sh`.

**Database looks stale after an update**
v1 backfills new columns additively on boot (no Alembic). If something seems off,
stop the backend, delete `services/core-api/miori.db`, and restart to recreate
it — or run `scripts/db-init.sh`.
