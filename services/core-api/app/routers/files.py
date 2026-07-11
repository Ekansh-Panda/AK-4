"""File upload / metadata endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.file import FileRecord
from app.schemas.common import StatusResponse
from app.schemas.file import FileDetail, FileOut
from app.services.files.service import FileIngestionService, UploadTooLargeError

router = APIRouter(prefix="/files", tags=["files"])


def _to_out(record: FileRecord) -> FileOut:
    return FileOut(
        id=record.id,
        created_at=record.created_at,
        updated_at=record.updated_at,
        user_id=record.user_id,
        filename=record.filename,
        content_type=record.content_type,
        size_bytes=record.size_bytes,
        status=record.status,
        has_text=bool(record.extracted_text),
    )


def _to_detail(record: FileRecord) -> FileDetail:
    return FileDetail(
        **_to_out(record).model_dump(),
        extracted_text=record.extracted_text,
    )


@router.post("", response_model=FileDetail)
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileDetail:
    service = FileIngestionService(db)
    data = await file.read()
    try:
        record = service.register_upload(
            file.filename or "upload.bin",
            data,
            content_type=file.content_type,
        )
    except UploadTooLargeError as exc:
        raise HTTPException(
            status_code=413,
            detail=f"file too large ({exc.size} bytes); limit is {exc.limit} bytes",
        ) from exc
    return _to_detail(record)


@router.post("/{file_id}/ingest", response_model=FileDetail)
async def ingest_file(
    file_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileDetail:
    service = FileIngestionService(db)
    try:
        record = await service.ingest(file_id)
        return _to_detail(record)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/search", response_model=list[dict])
def search_files(
    q: str, k: int = 5, user_id: str = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict]:
    service = FileIngestionService(db)
    results = service.search(query=q, limit=k)
    return [
        {
            "file_id": chunk.file_id,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "score": score
        }
        for chunk, score in results
    ]


@router.get("", response_model=list[FileOut])
def list_files(user_id: str = Depends(get_current_user), db: Session = Depends(get_db)) -> list[FileOut]:
    service = FileIngestionService(db)
    return [_to_out(r) for r in service.list()]


@router.get("/{file_id}", response_model=FileDetail)
def get_file(
    file_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileDetail:
    service = FileIngestionService(db)
    record = service.get(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="file not found")
    return _to_detail(record)


@router.delete("/{file_id}", response_model=StatusResponse)
def delete_file(
    file_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StatusResponse:
    service = FileIngestionService(db)
    if not service.delete(file_id):
        raise HTTPException(status_code=404, detail="file not found")
    return StatusResponse(detail="deleted")
