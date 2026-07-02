"""FileIngestionService — store uploaded files, extract text, track metadata.

Files are written under ``settings.UPLOAD_DIR``. On upload we best-effort
extract text for common text/code formats and PDFs (pypdf, lazy-imported). PDF
extraction degrades gracefully when pypdf is absent (lite-mode) — we store a
note and keep the upload.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.file import FileRecord

logger = get_logger(__name__)

# Extensions decoded directly as UTF-8 text (errors='replace').
TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".json",
    ".csv",
    ".log",
    # common code
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
    ".yaml",
    ".yml",
    ".toml",
    ".sh",
    ".rs",
    ".go",
    ".java",
}


class UploadTooLargeError(Exception):
    """Raised when an upload exceeds ``settings.MAX_UPLOAD_BYTES``."""

    def __init__(self, size: int, limit: int) -> None:
        self.size = size
        self.limit = limit
        super().__init__(f"upload of {size} bytes exceeds limit of {limit} bytes")


class FileIngestionService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._upload_dir = Path(settings.UPLOAD_DIR)
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    # --- extraction ---
    @staticmethod
    def _extract_text(filename: str, data: bytes) -> tuple[str | None, str]:
        """Return (extracted_text, status). status is "ingested" or "uploaded"."""
        ext = Path(filename).suffix.lower()
        if ext in TEXT_EXTENSIONS:
            return data.decode("utf-8", errors="replace"), "ingested"
        if ext == ".pdf":
            return FileIngestionService._extract_pdf(data)
        # Unknown/binary: keep as-is, no text.
        return None, "uploaded"

    @staticmethod
    def _extract_pdf(data: bytes) -> tuple[str | None, str]:
        try:
            import io

            import pypdf  # lazy / optional
        except ImportError:
            logger.info("pypdf not installed; storing PDF without text extraction")
            return "[pdf text extraction unavailable: pypdf not installed]", "uploaded"
        try:
            reader = pypdf.PdfReader(io.BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            return text.strip() or None, "ingested"
        except Exception as exc:  # noqa: BLE001 - never crash on bad PDFs
            logger.warning("PDF extraction failed: %s", exc)
            return f"[pdf text extraction failed: {exc}]", "failed"

    # --- ingestion ---
    def register_upload(
        self,
        filename: str,
        data: bytes,
        *,
        content_type: str | None = None,
        user_id: str | None = None,
    ) -> FileRecord:
        """Persist bytes to disk, extract text, and record metadata.

        Raises ``UploadTooLargeError`` if the payload exceeds the configured max.
        """
        if len(data) > settings.MAX_UPLOAD_BYTES:
            raise UploadTooLargeError(len(data), settings.MAX_UPLOAD_BYTES)

        safe_name = Path(filename).name or "upload.bin"
        stored_name = f"{uuid.uuid4()}_{safe_name}"
        path = self._upload_dir / stored_name
        path.write_bytes(data)

        extracted, status = self._extract_text(safe_name, data)

        record = FileRecord(
            filename=safe_name,
            content_type=content_type,
            size_bytes=len(data),
            storage_path=str(path),
            status=status,
            user_id=user_id,
            extracted_text=extracted,
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        logger.info(
            "Registered upload %s (%d bytes, status=%s)", safe_name, len(data), status
        )
        return record

    async def ingest(self, file_id: str) -> FileRecord:
        record = self._db.get(FileRecord, file_id)
        if not record:
            raise ValueError("file not found")

        from app.core.config import get_effective_bool
        from app.core.config import settings

        semantic_enabled = get_effective_bool(self._db, "semantic_memory_enabled", settings.SEMANTIC_MEMORY_ENABLED)
        if not semantic_enabled:
            raise ValueError("Semantic memory disabled")

        if record.status == "ingested":
            return record

        if not record.extracted_text:
            raise ValueError("no text to ingest")

        text = record.extracted_text
        words = text.split()
        chunk_size = 500
        chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

        from app.models.file_chunk import FileChunk
        
        for idx, chunk in enumerate(chunks):
            # If semantic memory is on, embed it!
            embedding = None
            if semantic_enabled:
                from app.services.memory.embedding_memory import EmbeddingMemoryProvider
                # Avoid loading the whole provider if we just need the embedding function,
                # but since it's already there, use it.
                provider = EmbeddingMemoryProvider(self._db)
                embedding = provider._encode(chunk).tolist() if hasattr(provider, "_encode") else None

            row = FileChunk(
                file_id=file_id,
                chunk_index=idx,
                content=chunk,
                embedding=embedding
            )
            self._db.add(row)
        
        record.status = "ingested"
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return record

    def list(self) -> list[FileRecord]:
        return list(self._db.execute(select(FileRecord)).scalars().all())

    def get(self, file_id: str) -> FileRecord | None:
        return self._db.get(FileRecord, file_id)

    def delete(self, file_id: str) -> bool:
        record = self._db.get(FileRecord, file_id)
        if not record:
            return False
        try:
            Path(record.storage_path).unlink(missing_ok=True)
        except OSError as exc:  # pragma: no cover - defensive
            logger.warning("Could not delete file %s: %s", record.storage_path, exc)
        self._db.delete(record)
        self._db.commit()
        return True

    def search(self, query: str, limit: int = 5) -> list[tuple[FileChunk, float]]:
        """Search file chunks. Returns (chunk, score)."""
        from app.core.config import get_effective_bool
        from app.core.config import settings
        from app.models.file_chunk import FileChunk
        
        semantic_enabled = get_effective_bool(self._db, "semantic_memory_enabled", settings.SEMANTIC_MEMORY_ENABLED)
        
        if semantic_enabled:
            try:
                from app.services.memory.embedding_memory import EmbeddingMemoryProvider
                provider = EmbeddingMemoryProvider(self._db)
                if hasattr(provider, "_encode") and hasattr(FileChunk, "embedding"):
                    query_emb = provider._encode(query).tolist()
                    # Using SQLite cosine similarity trick from EmbeddingMemoryProvider
                    from sqlalchemy import func
                    import json
                    # We can't do exact distance in raw SQLite easily without vector extensions.
                    # Wait! EmbeddingMemoryProvider loads all rows and does numpy dot product!
                    # Let's do exactly what EmbeddingMemoryProvider does.
                    rows = self._db.execute(select(FileChunk).where(FileChunk.embedding.isnot(None))).scalars().all()
                    import numpy as np
                    scored = []
                    for r in rows:
                        try:
                            # In SQLite JSON columns, it might come back as string or list
                            arr = r.embedding if isinstance(r.embedding, list) else json.loads(r.embedding)
                            score = float(np.dot(query_emb, arr))
                            scored.append((r, score))
                        except Exception:
                            continue
                    scored.sort(key=lambda x: x[1], reverse=True)
                    return scored[:limit]
            except Exception as e:
                logger.warning("File chunk semantic search failed, falling back to LIKE: %s", e)
        
        # Lite-mode / fallback: substring match
        stmt = select(FileChunk).where(FileChunk.content.ilike(f"%{query}%")).limit(limit)
        rows = self._db.execute(stmt).scalars().all()
        return [(r, 1.0) for r in rows]
