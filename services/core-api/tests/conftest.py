"""Pytest fixtures — in-memory SQLite session, no network required.

Run: ``cd services/core-api && pytest`` (needs ``pip install -r requirements.txt``
for pytest; the app deps are already required to import the package).
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base


@pytest.fixture()
def db() -> Session:
    import app.models  # noqa: F401 - register tables

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, future=True
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
