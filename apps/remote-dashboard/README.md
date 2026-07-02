# Miori Core — Remote Dashboard

A mobile-first web app to reach the Miori host machine from your phone: chat
with Miori, watch the host's vitals, wake or sleep her, and send files over —
all from your pocket, over the local network.

It shares Miori Core's visual language with the desktop shell (near-black glass,
a single warm violet accent, calm motion). The remote is a friend in your
pocket, not a control panel.

> **Status:** Wired to the live **core-api** with an automatic offline mock
> fallback. `src/lib/api.ts` probes the host on connect and talks to the real
> endpoints when reachable; if the host can't be reached (or a call fails
> mid-flight) it transparently falls back to fabricated data so the app stays
> fully explorable with no backend. Offline/mocked surfaces are clearly labelled
> in the UI.

## Stack

React 18 · TypeScript · Vite 5 · Tailwind CSS 3 · react-router-dom 6 ·
lucide-react · clsx. No `shadcn` runtime dependency — the small component set
lives in `src/components`.

## Run it

### 1. Start the backend (`services/core-api`)

For device + power features the API must run with **`REMOTE_ENABLED=true`**
(it's the default in `app/core/config.py`, but make it explicit for clarity).
Bind to all interfaces so your phone can reach it over the LAN:

```bash
cd services/core-api
REMOTE_ENABLED=true uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Without `REMOTE_ENABLED=true` the `/api/remote/*` routes are not mounted; the
dashboard still runs but the **Device** and **Power** tabs show a clear
"remote control disabled" state (chat, files, and tasks keep working).

### 2. Start the dashboard

From this folder (`apps/remote-dashboard`):

```bash
npm install      # first time only
npm run dev      # Vite dev server on 0.0.0.0:5174 (LAN-accessible)
```

Then, on your **phone on the same Wi-Fi**, open:

```
http://<your-computer-LAN-ip>:5174
```

On the login screen, enter the **host address** as
`http://<your-computer-LAN-ip>:8000` (the core-api), plus a pairing token, and
tap Connect.

(`vite.config.ts` sets `server.host = true`, so the dev server binds to all
interfaces. Find your LAN IP with `ipconfig` / `ifconfig` / `ip addr`.)

Other scripts:

```bash
npm run build      # type-check (tsc) then production build to dist/
npm run preview    # serve the production build, also LAN-bound on :5174
npm run typecheck  # tsc --noEmit
```

`base` is `"./"` so the built `dist/` can be served from any path — including
mounted behind the FastAPI core-api later (e.g. at `/remote`).

## Environment variables

| Var              | Default | Purpose                                                                                          |
| ---------------- | ------- | ------------------------------------------------------------------------------------------------ |
| `VITE_MIORI_API` | `/api`  | API path appended to the connected host, or an absolute base URL. Health is always probed at the host origin (`/health`), independent of this. |

There is no build-time host/token: the **host address** and **pairing token**
are entered at runtime on the login screen and persisted to `localStorage`
(`src/state/connection.tsx`). Set `VITE_MIORI_API` only if your core-api mounts
the API somewhere other than `/api`.

## Live vs. offline mock

`src/lib/api.ts` is the single source of host I/O and decides live-vs-mock at
runtime:

- **On connect** it probes `GET {host}/health`. A healthy response switches the
  client to **live** mode and records the host version + whether
  `REMOTE_ENABLED` is on.
- If the host is **unreachable** (or any later call times out / errors), the
  client transparently falls back to the **offline mock** — every screen still
  works with simulated data, clearly labelled "Offline".
- If the host is reachable but started **without** `REMOTE_ENABLED=true`, the
  Device/Power tabs show a clear **"remote control disabled"** state instead of
  failing; chat, files, and tasks remain live.

Connection state (Live / Offline demo / remote-enabled) is shown on the
**Settings** screen and in the header connection chip.

## Screens

| Tab          | File                              | What it does                                                       |
| ------------ | --------------------------------- | ------------------------------------------------------------------ |
| (Login)      | `src/screens/LoginScreen.tsx`     | Host address + token, "Connect" (probes `/health`)                 |
| Chat         | `src/screens/ChatScreen.tsx`      | Remote chat via `POST /api/chat`, typed-in reply                   |
| Device       | `src/screens/DeviceScreen.tsx`    | Online state, device + task counts, task list; remote-disabled aware |
| Power        | `src/screens/PowerScreen.tsx`     | Wake / Sleep the primary device via `/api/remote/devices/{id}/…`   |
| Files        | `src/screens/FilesScreen.tsx`     | Upload via `POST /api/files` (real progress) + host file listing   |
| Settings     | `src/screens/SettingsScreen.tsx`  | Host, token, live/offline status, theme, disconnect                |

A persistent connection chip (`src/components/ConnectionChip.tsx`) lives in
every header, and a glassy bottom tab bar (`src/components/BottomNav.tsx`) is
safe-area aware for notch / home-indicator phones.

## How it connects to the backend

All host I/O goes through the typed client in **`src/lib/api.ts`**, which talks
to **`services/core-api`** (`REMOTE_ENABLED` flag in `app/core/config.py`).

| Client method     | Real endpoint                                                              |
| ----------------- | -------------------------------------------------------------------------- |
| `connect`         | `GET  {host}/health`                                                       |
| `sendMessage`     | `POST {host}/api/chat` `{ message, session_id? }` → `{ session_id, reply }` |
| `getDeviceStatus` | `GET  {host}/health` + `GET {host}/api/remote/devices` (synthesised)       |
| `getTasks`        | `GET  {host}/api/tasks`                                                     |
| `setPowerState`   | `POST {host}/api/remote/devices/{id}/wake` \| `…/sleep`                     |
| `uploadFile`      | `POST {host}/api/files` (multipart, field `file`) — real XHR progress      |
| `getFiles`        | `GET  {host}/api/files`                                                     |

Notes:

- The API base is `VITE_MIORI_API` (default `/api`) appended to the host;
  `/health` is probed at the host **origin** (no `/api`).
- The core-api has no single `/remote/status` route, so device status is
  **synthesised** from `/health` (online) + `/remote/devices` (power state of
  the first device). The chat session id from the first reply is reused on
  subsequent turns for multi-turn context.
- The `/api/remote/*` endpoints exist **only** when `REMOTE_ENABLED=true`; the
  client treats their absence (404) as "remote disabled" rather than an error.

Auth is sent as `Authorization: Bearer <token>` plus an `X-Miori-Remote: 1`
header. The host address and token are kept in `src/state/connection.tsx` and
persisted to `localStorage`.

## Security note (read this)

This dashboard is designed for **LAN-only** use — your phone and the Miori host
on the same trusted network.

- The pairing **token is stored in `localStorage`** in plain text. That's
  acceptable for a short-lived, single-purpose LAN pairing token, but do **not**
  reuse a long-lived or high-value secret here.
- There is **no transport encryption** assumed by default (`http://`). Do not
  expose the host directly to the public internet. If remote-over-WAN is ever
  needed, front it with a VPN / reverse proxy with TLS and proper auth — do not
  port-forward the raw core-api.
- The token is forwarded to the host as a bearer header; actual validation is
  host-side. When the host is unreachable the client falls back to the offline
  mock, so the demo never hard-fails — but no real token check happens in that
  fallback path.

## Project layout

```
apps/remote-dashboard/
├─ index.html                 viewport-fit=cover, theme-color, PWA meta
├─ vite.config.ts             base "./", server.host true (LAN)
├─ tailwind.config.ts         shared Miori design tokens
├─ tsconfig*.json
├─ postcss.config.js
├─ public/favicon.svg
└─ src/
   ├─ main.tsx                Router + ConnectionProvider
   ├─ App.tsx                 Routes + auth guard + bottom-nav shell
   ├─ index.css               Tailwind + glass + safe-area utilities + tokens
   ├─ lib/
   │  ├─ api.ts               typed host client (live + offline mock fallback)
   │  ├─ types.ts             shared types (aligned to core-api schemas)
   │  ├─ mock.ts              offline fallback data + helpers
   │  └─ cn.ts                class-name joiner
   ├─ state/
   │  ├─ connection.tsx       host/token/theme/status/remote-enabled context (persisted)
   │  └─ chat.tsx             chat messages + typed reply
   ├─ components/
   │  ├─ BottomNav.tsx
   │  ├─ ConnectionChip.tsx
   │  ├─ ScreenHeader.tsx
   │  ├─ GlassCard.tsx
   │  ├─ Button.tsx
   │  ├─ StatusDot.tsx
   │  └─ PresenceOrb.tsx
   └─ screens/
      ├─ LoginScreen.tsx
      ├─ ChatScreen.tsx
      ├─ DeviceScreen.tsx
      ├─ PowerScreen.tsx
      ├─ FilesScreen.tsx
      └─ SettingsScreen.tsx
```
