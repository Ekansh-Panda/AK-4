"""Database engine, session factory and dependency wiring."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger
from app.db.base import Base
from app.models.setting import Setting
from app.models.user import User

logger = get_logger(__name__)

# Constants for default user creation
DEFAULT_USER_KEY = "default_user_id"
DEFAULT_USERNAME = "miori-local"
DEFAULT_DISPLAY_NAME = "Miori Local"

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


def ensure_default_user(db: Session | None = None) -> None:
    """Create default user if none exists, storing id in settings.

    Called on every boot to guarantee a user exists.
    """
    close_when_done = False
    if db is None:
        db = SessionLocal()
        close_when_done = True

    try:
        result = db.execute(select(User).limit(1)).scalar_one_or_none()
        if result:
            return

        user = User(
            username=DEFAULT_USERNAME,
            display_name=DEFAULT_DISPLAY_NAME,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        setting = Setting(key=DEFAULT_USER_KEY, value=user.id)
        db.add(setting)
        db.commit()
    finally:
        if close_when_done:
            db.close()


def init_db() -> None:
    """Create all tables. Imports models so they register with the metadata."""
    # Import models for side effects (table registration).
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_columns()
    ensure_default_user()
    logger.info("Database initialized at %s", settings.DATABASE_URL)


# Tiny additive "migration": SQLAlchemy create_all never ALTERs existing tables,
# so newly-added columns are backfilled here for already-created SQLite DBs.
# Each entry: (table, column, column DDL type + default).
_ADDED_COLUMNS: list[tuple[str, str, str]] = [
    ("files", "extracted_text", "TEXT"),
    ("memories", "pinned", "BOOLEAN DEFAULT 0"),
    ("memories", "embedding", "TEXT"),
    ("chat_sessions", "project_id", "TEXT"),
    ("tasks", "project_id", "TEXT"),
    ("files", "project_id", "TEXT"),
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
