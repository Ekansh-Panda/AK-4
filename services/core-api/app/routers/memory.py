"""Memory REST endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.memory import Memory
from app.schemas.common import StatusResponse
from app.schemas.memory import (
    MemoryCreate,
    MemoryOut,
    MemorySearchRequest,
    MemorySearchResult,
    MemoryUpdate,
)
from app.services.memory.service import MemoryService

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("", response_model=MemoryOut)
async def add_memory(body: MemoryCreate, db: Session = Depends(get_db)) -> MemoryOut:
    service = MemoryService(db)
    item = await service.add(
        body.content,
        namespace=body.namespace,
        user_id=body.user_id,
        meta=body.meta,
        pinned=body.pinned,
    )
    row = db.get(Memory, item.id)
    return MemoryOut.model_validate(row)


@router.get("", response_model=list[MemoryOut])
def list_memory(
    kind: str | None = Query(None, description="Filter by namespace/kind"),
    pinned: bool | None = Query(None, description="Filter by pinned state"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[MemoryOut]:
    service = MemoryService(db)
    out: list[MemoryOut] = []
    for item in service.list(kind=kind, pinned=pinned, limit=limit):
        row = db.get(Memory, item.id)
        if row:
            out.append(MemoryOut.model_validate(row))
    return out


@router.post("/search", response_model=list[MemorySearchResult])
async def search_memory(
    body: MemorySearchRequest, db: Session = Depends(get_db)
) -> list[MemorySearchResult]:
    service = MemoryService(db)
    results: list[MemorySearchResult] = []
    for item in await service.search(body.query, namespace=body.namespace, limit=body.limit):
        row = db.get(Memory, item.id)
        if row:
            results.append(
                MemorySearchResult(
                    memory=MemoryOut.model_validate(row), score=item.score
                )
            )
    return results


@router.get("/{memory_id}", response_model=MemoryOut)
def get_memory(memory_id: str, db: Session = Depends(get_db)) -> MemoryOut:
    row = db.get(Memory, memory_id)
    if not row:
        raise HTTPException(status_code=404, detail="memory not found")
    return MemoryOut.model_validate(row)


@router.patch("/{memory_id}", response_model=MemoryOut)
def update_memory(
    memory_id: str, body: MemoryUpdate, db: Session = Depends(get_db)
) -> MemoryOut:
    service = MemoryService(db)
    item = service.update(memory_id, content=body.content, pinned=body.pinned)
    if not item:
        raise HTTPException(status_code=404, detail="memory not found")
    row = db.get(Memory, item.id)
    return MemoryOut.model_validate(row)


@router.delete("/{memory_id}", response_model=StatusResponse)
def delete_memory(memory_id: str, db: Session = Depends(get_db)) -> StatusResponse:
    service = MemoryService(db)
    if not service.delete(memory_id):
        raise HTTPException(status_code=404, detail="memory not found")
    return StatusResponse(detail="deleted")
