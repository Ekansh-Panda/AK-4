"""File schemas."""

from __future__ import annotations

from app.schemas.common import TimestampedORMModel


class FileOut(TimestampedORMModel):
    """Lightweight view used by the list endpoint — no full extracted text."""

    user_id: str | None = None
    filename: str
    content_type: str | None = None
    size_bytes: int
    # NOTE: ``storage_path`` is intentionally NOT exposed here — it leaks the
    # server filesystem layout. The ORM model keeps it for internal use.
    status: str
    # Whether extracted text is available (cheap boolean; full text via detail).
    has_text: bool = False


class FileDetail(FileOut):
    """Detail view (GET /files/{id}) — includes the full extracted text."""

    extracted_text: str | None = None


class FileChunkOut(TimestampedORMModel):
    """View of a single indexed file chunk."""

    file_id: str
    chunk_index: int
    content: str
    score: float | None = None
