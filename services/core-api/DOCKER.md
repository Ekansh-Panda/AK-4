# Miori Core API — Docker

Run the backend API in a container. The image installs only core runtime
deps (FastAPI, uvicorn, SQLAlchemy, pydantic-settings) so the app boots in
**lite mode** without any ML/torch dependencies.

## Build

```bash
docker build -t miori-core-api ./services/core-api
```

## Run (standalone)

```bash
docker run --rm -p 8000:8000 \
  -e HOST=0.0.0.0 -e PORT=8000 -e LITE_MODE=true \
  miori-core-api
```

The API will be available at http://localhost:8000 (OpenAPI docs at
`/docs`).

## Run with Docker Compose

```bash
docker compose up --build
```

This starts the `backend` service, publishes `8000:8000`, sets the sane
defaults (`LITE_MODE`, `REMOTE_ENABLED`, `SCHEDULER_ENABLED`), and persists
the SQLite database in a named volume (`miori-data`).

### Configuration

All config is via environment variables (see
`services/core-api/app/core/config.py`). No secrets are baked into the
image. Provide provider API keys at runtime, e.g.:

```bash
OPENAI_API_KEY=sk-... docker compose up
```

A local `services/core-api/.env` file is **not** required; if you have one
you can mount it:

```bash
docker run --rm -p 8000:8000 -v "$PWD/services/core-api/.env:/app/.env" miori-core-api
```

## Notes

- The image uses `python:3.12-slim` and runs as root (acceptable for this brief).
- `uvicorn app.main:app --host 0.0.0.0 --port 8000` is the container entrypoint.
- The optional remote dashboard is out of scope (native Tauri build); see the
  commented example in `docker-compose.yml` to add it later.
