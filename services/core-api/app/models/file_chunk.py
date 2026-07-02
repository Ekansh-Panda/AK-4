"""File Chunk model."""

from datetime import datetime
import uuid
from typing import Any

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class FileChunk(Base):
    __tablename__ = "file_chunks"

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id: str = Column(String(36), ForeignKey("files.id", ondelete="CASCADE"), index=True, nullable=False)
    chunk_index: int = Column(Integer, nullable=False)
    content: str = Column(Text, nullable=False)
    embedding: Any = Column(JSON, nullable=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)

    file = relationship("FileRecord", backref="chunks")
