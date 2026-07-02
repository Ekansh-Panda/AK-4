# Miori Core — Overnight Build Mission

## Product
Miori Core is a cross-platform personal AI workstation and desktop companion.
It must feel like a friend, not a servant or a corporate assistant.

## Primary goals for tonight
Build a working v0.1 foundation, not a fully complete AI.

## Hard constraints
- New architecture, not direct repo-merging
- Cross-platform: Windows, Linux, macOS
- Must stay usable on low-end machines
- Minimal dark elegant UI
- Persona = warm, sharp, emotionally alive, friend-like
- Remote dashboard required
- Backend must be modular and extensible
- SQLite default
- Heavy features must be optional / lazy-loaded

## Tech stack
- Tauri + React + TypeScript + Tailwind + shadcn/ui
- Python FastAPI backend
- WebSocket streaming
- SQLAlchemy + SQLite
- Clean modular monorepo

## Required deliverables by morning
1. Monorepo structure
2. Desktop app shell
3. Remote dashboard shell
4. Backend skeleton with routes and services
5. Shared design system
6. Persona system skeleton
7. Memory/tool/provider abstractions
8. Repo analysis docs
9. Integration feature matrix
10. README with run instructions

## Design requirements
Miori must feel like a friend, not a tool.
No bloated Jarvis cockpit UI.
Use subtle motion, clean spacing, elegant dark visuals.

## Pages required
- Chat
- Files
- Memory
- Projects (placeholder okay)
- Research (placeholder okay)
- Tasks
- Remote
- Settings

## Backend modules required
- chat
- memory
- providers
- persona
- files
- remote
- tasks
- websocket status

## Important donor repos
- Mark-XLVI / MARK-XL
- Odysseus
- Khoj
- selected computer-use repos
Use them for ideas, architecture analysis, and selective feature harvesting only.
Do not dump their code blindly into the new repo.

## Deliverable quality bar
Everything should compile or be scaffolded cleanly.
Where a feature is not implemented yet, create clean interfaces, TODOs, and docs.
