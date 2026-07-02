# Miori Core — Desktop

The desktop companion shell for **Miori Core**, a personal AI friend +
workstation. Built with **Tauri v2 + React + TypeScript + Vite + TailwindCSS**.

Miori is designed to feel like a friend, not a servant — minimal, dark, glassy,
with a small "presence orb" that breathes with her state. See
[`UI_SPEC.md`](./UI_SPEC.md) for the full design system.

---

## Prerequisites

- **Node.js** 18+ and npm
- For the native desktop build only: **Rust** (stable) and the
  [Tauri v2 system prerequisites](https://v2.tauri.app/start/prerequisites/)
  for your OS (webview, build tools, etc.)

The Python FastAPI backend is **optional**. With no backend running, every data
call falls back to local mock data and chat streams a canned reply, so the whole
shell is usable offline.

---

## Install

```bash
cd apps/desktop
npm install
```

## Run — web (fastest, no Rust needed)

```bash
npm run dev
```

Opens the Vite dev server at `http://localhost:1420`. This renders the entire UI
in the browser using mocks.

## Run — native desktop (Tauri)

```bash
npm run tauri dev
```

This launches the Tauri window (1200×800, dark) and runs the Vite dev server
underneath. Requires the Rust/Tauri prerequisites above.

> First native build only: generate app icons once with
> `npm run tauri icon path/to/source-1024.png` (see `src-tauri/icons/README.md`).

## Build

```bash
npm run build        # typecheck + Vite production build (web bundle -> dist/)
npm run tauri build  # package the native desktop app
```

## Other scripts

```bash
npm run typecheck    # tsc --noEmit
npm run preview      # preview the built web bundle
```

---

## Connecting a backend

The app talks to the **Miori Core API** (`services/core-api`, FastAPI). It is
wired to the real contract but the backend stays **optional** — every call
degrades gracefully to mock/empty data so the shell never hard-crashes offline.

By default the app targets:

- HTTP API: `http://localhost:8000/api`
- Chat WebSocket: `ws://localhost:8000/ws/chat`

Override via env (Vite picks these up):

```bash
# apps/desktop/.env
VITE_MIORI_API=http://localhost:8000/api
VITE_MIORI_WS=ws://localhost:8000/ws/chat
```

### What talks to what

All HTTP lives in [`src/lib/api.ts`](./src/lib/api.ts), a typed client whose
request/response shapes mirror `services/core-api/app/schemas/*.py` exactly:

| Area     | Endpoints                                                                              |
| -------- | -------------------------------------------------------------------------------------- |
| Chat     | `POST /chat`, `POST /chat/sessions`, `GET /chat/sessions/{id}/messages`, `WS /ws/chat` |
| Memory   | `GET/POST /memory` (`?kind=&pinned=&limit=`), `POST /memory/search`, `GET/PATCH/DELETE /memory/{id}` |
| Files    | `POST /files` (multipart), `GET /files`, `GET /files/{id}`, `DELETE /files/{id}`       |
| Tasks    | `GET/POST /tasks`, `GET/PATCH/DELETE /tasks/{id}`                                       |
| Persona  | `GET /persona`, `GET /persona/modes`, `POST /persona/mode`                              |
| Providers| `GET /providers`, `GET /providers/models`, `GET /providers/status`, `PUT /providers/active` |
| Settings | `GET/PUT /settings`, `GET/DELETE /settings/{key}`                                       |
| Remote   | `GET /remote/devices`, `GET /remote/sessions` (read-only-ish; gated on `remote_enabled`) |
| Health   | `GET /health` (server root — the client strips `/api` from the base)                   |

- **Chat** (`state/ChatStore.tsx`) creates/loads a session, hydrates history,
  then streams replies over `WS /ws/chat` via `src/lib/ws.ts`. The Chat view
  shows the live persona mode + active provider; both fall back to "mock" when
  the socket/HTTP is unreachable.
- **Files** uploads via `FormData`; oversize (>25 MB) is caught client-side and
  the server's `413` is surfaced as a friendly notice. Click a file to preview
  its `extracted_text`.
- **Memory / Tasks** are full CRUD with pin/edit/delete (memory) and
  status-toggle/delete (tasks); optimistic updates re-sync from the server.
- **Settings** drives the active provider (`PUT /providers/active`), the backend
  persona mode (`POST /persona/mode`), and a **Lite mode** toggle persisted via
  `PUT /settings` under the `lite_mode` key.
- **Connection** (`state/ConnectionStore.tsx`) polls `GET /health` +
  `GET /providers/status` to drive the presence/connection badge and the
  active-model indicator. Polling backs off politely (15 s when up, 30 s when
  down) and never tight-loops.

### Offline / fallback behavior

When a call fails or times out (~2.5 s), the client returns a sensible fallback
(mock data or an empty list) and the status bar shows **"Offline · mocks."**
Mutations against a down backend update the UI optimistically but won't persist;
affected views show a small "changes won't persist" hint.

---

## Project structure

```
apps/desktop/
├── index.html
├── package.json
├── tailwind.config.ts        # dark theme tokens
├── tsconfig.json / tsconfig.node.json
├── vite.config.ts            # "@/" alias -> src/, dev port 1420
├── postcss.config.js
├── public/vite.svg
├── UI_SPEC.md                # design system
├── src-tauri/                # Tauri v2 host (Rust)
│   ├── Cargo.toml
│   ├── build.rs
│   ├── tauri.conf.json       # com.miori.core, 1200x800, dark
│   ├── capabilities/default.json
│   ├── icons/README.md
│   └── src/{main.rs, lib.rs}
└── src/
    ├── main.tsx              # entry + BrowserRouter
    ├── App.tsx               # providers + routes
    ├── index.css             # Tailwind + CSS variables + glass recipe
    ├── vite-env.d.ts
    ├── lib/                  # cn, types, api, ws, mockData
    ├── components/ui/        # Button, Card, GlassPanel, Input, Avatar, StatusBadge, ScrollArea
    ├── components/layout/    # AppShell, LeftRail, RightPanel, TopBar, Composer, PresenceOrb, PageContainer
    ├── features/             # one folder per page (chat, files, memory, projects, research, tasks, remote, settings)
    └── state/                # ChatStore, PersonaStore, ConnectionStore (context + useReducer)
```

---

## Pages

Chat · Files · Memory · Projects · Research · Tasks · Remote · Settings.
Projects and Research are intentional placeholders for v0.1.
