"""Database engine, session factory and dependency wiring."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger
from app.db.base import Base

logger = get_logger(__name__)

# SQLite needs `check_same_thread=False` to be shared across FastAPI threads.
_connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
)


def init_db() -> None:
    """Create all tables. Imports models so they register with the metadata."""
    # Import models for side effects (table registration).
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_columns()
    logger.info("Database initialized at %s", settings.DATABASE_URL)


# Tiny additive "migration": SQLAlchemy create_all never ALTERs existing tables,
# so newly-added columns are backfilled here for already-created SQLite DBs.
# Each entry: (table, column, column DDL type + default).
_ADDED_COLUMNS: list[tuple[str, str, str]] = [
    ("files", "extracted_text", "TEXT"),
    ("memories", "pinned", "BOOLEAN DEFAULT 0"),
    ("memories", "embedding", "TEXT"),
]


def _ensure_columns() -> None:
    from sqlalchemy import inspect, text

    try:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        with engine.begin() as conn:
            for table, column, ddl in _ADDED_COLUMNS:
                if table not in existing_tables:
                    continue
                cols = {c["name"] for c in inspector.get_columns(table)}
                if column not in cols:
                    conn.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
                    )
                    logger.info("Added column %s.%s", table, column)
    except Exception as exc:  # noqa: BLE001 - best-effort, never block boot
        logger.warning("Column backfill skipped: %s", exc)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
