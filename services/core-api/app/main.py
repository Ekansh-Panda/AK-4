"""Miori Core API — FastAPI application factory.

Run locally:
    uvicorn app.main:app --reload

This boots a fully offline-capable backend: chat works through a mock provider,
memory uses SQLite, and remote/persona/tasks are wired with clean stubs.

Donor-repo integration points are marked with TODOs throughout:
  - Mark-XLVI  -> remote control transport
  - Odysseus   -> real model providers + vector memory
  - Khoj       -> memory ingestion + task scheduling
  - computer-use -> sandboxed tools
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import init_db
from app.routers import (
    audio,
    chat,
    files,
    health,
    memory,
    persona,
    projects,
    providers,
    remote,
    research,
    settings as settings_router,
    tasks,
    tools,
)
from app.services.tools.examples import register_example_tools
from app.ws import chat as ws_chat
from app.ws import remote as ws_remote
from app.ws import status as ws_status

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create DB tables and register built-in tools.
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    init_db()
    register_example_tools()

    # Hydrate the active provider selection from persisted settings, then log a
    # concise availability summary. Mock is always available, so this never
    # blocks boot.
    from app.db.session import SessionLocal
    from app.services.providers.registry import registry as provider_registry

    db = SessionLocal()
    try:
        active = provider_registry.load_active(db)
    finally:
        db.close()

    avail = provider_registry.availability()
    configured = [a.name for a in avail if a.configured]
    logger.info("DB path: %s", settings.DATABASE_URL)
    logger.info("Lite mode: %s", settings.LITE_MODE)
    logger.info(
        "Providers — active=%s, configured=%s",
        active,
        ", ".join(configured) if configured else "none (mock only)",
    )
    for a in avail:
        logger.info(
            "  provider %-8s configured=%s available=%s",
            a.name,
            a.configured,
            a.available,
        )
    logger.info(
        "Boot complete (lite_mode=%s, remote_enabled=%s)",
        settings.LITE_MODE,
        settings.REMOTE_ENABLED,
    )
    
    from app.services.tasks.scheduler import start_scheduler, shutdown_scheduler
    start_scheduler()
    
    yield
    # Shutdown.
    shutdown_scheduler()
    logger.info("Shutting down %s", settings.APP_NAME)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    # Credentials + a "*" wildcard origin is invalid/unsafe per the CORS spec,
    # so only allow credentials when origins are explicit (the default).
    allow_credentials = "*" not in settings.CORS_ORIGINS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health (no /api prefix so it's easy to probe).
    app.include_router(health.router)

    # Domain routers under /api.
    api_routers = [
        audio.router,
        chat.router,
        memory.router,
        files.router,
        projects.router,
        providers.router,
        persona.router,
        research.router,
        tasks.router,
        tools.router,
        settings_router.router,
    ]
    if settings.REMOTE_ENABLED:
        api_routers.append(remote.router)
    for r in api_routers:
        app.include_router(r, prefix="/api")

    # WebSocket routers (no prefix; paths already start with /ws).
    app.include_router(ws_chat.router)
    app.include_router(ws_status.router)
    if settings.REMOTE_ENABLED:
        app.include_router(ws_remote.router)

    return app


app = create_app()
