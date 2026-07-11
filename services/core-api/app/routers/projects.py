"""Projects CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.file import FileRecord
from app.models.project import Project
from app.models.session import ChatSession
from app.models.task import Task
from app.schemas.common import StatusResponse

router = APIRouter(prefix="/projects", tags=["projects"])


# --- schemas ---
class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    brief: str | None = None
    session_ids: list[str] | None = None
    task_ids: list[str] | None = None
    file_ids: list[str] | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    brief: str | None = None
    session_ids: list[str] | None = None
    task_ids: list[str] | None = None
    file_ids: list[str] | None = None


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str | None
    status: str
    brief: str | None
    created_at: str | None = None
    updated_at: str | None = None
    sessions: list[dict] = []
    tasks: list[dict] = []
    files: list[dict] = []

    model_config = {"from_attributes": True}


def _linked_items(db: Session, project_id: str) -> dict[str, list[dict]]:
    sessions = [
        {"id": s.id, "title": s.title}
        for s in db.execute(
            select(ChatSession).where(ChatSession.project_id == project_id)
        )
        .scalars()
        .all()
    ]
    tasks = [
        {"id": t.id, "title": t.title}
        for t in db.execute(select(Task).where(Task.project_id == project_id))
        .scalars()
        .all()
    ]
    files = [
        {"id": f.id, "filename": f.filename}
        for f in db.execute(select(FileRecord).where(FileRecord.project_id == project_id))
        .scalars()
        .all()
    ]
    return {"sessions": sessions, "tasks": tasks, "files": files}


def _to_out(p: Project, db: Session | None = None) -> ProjectOut:
    linked = _linked_items(db, p.id) if db is not None else {}
    return ProjectOut(
        id=p.id,
        name=p.name,
        description=p.description,
        status=p.status,
        brief=p.brief,
        created_at=str(p.created_at) if p.created_at else None,
        updated_at=str(p.updated_at) if p.updated_at else None,
        **linked,
    )


# --- routes ---
@router.post("", response_model=ProjectOut)
def create_project(
    body: ProjectCreate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectOut:
    project = Project(name=body.name, description=body.description, brief=body.brief)
    db.add(project)
    db.commit()
    db.refresh(project)
    _link_items(db, project.id, body.session_ids, body.task_ids, body.file_ids)
    db.commit()
    db.refresh(project)
    return _to_out(project, db)


def _link_items(
    db: Session,
    project_id: str,
    session_ids: list[str] | None,
    task_ids: list[str] | None,
    file_ids: list[str] | None,
) -> None:
    """Link existing sessions/tasks/files to a project by id (optional)."""
    if session_ids:
        for s in db.execute(
            select(ChatSession).where(ChatSession.id.in_(session_ids))
        ).scalars().all():
            s.project_id = project_id
    if task_ids:
        for t in db.execute(
            select(Task).where(Task.id.in_(task_ids))
        ).scalars().all():
            t.project_id = project_id
    if file_ids:
        for f in db.execute(
            select(FileRecord).where(FileRecord.id.in_(file_ids))
        ).scalars().all():
            f.project_id = project_id


@router.get("", response_model=list[ProjectOut])
def list_projects(
    status: str | None = None,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProjectOut]:
    stmt = select(Project).order_by(Project.created_at.desc())
    if status:
        stmt = stmt.where(Project.status == status)
    rows = db.execute(stmt).scalars().all()
    return [_to_out(r, db) for r in rows]


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectOut:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="project not found")
    return _to_out(p, db)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: str,
    body: ProjectUpdate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectOut:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="project not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        if field in ("session_ids", "task_ids", "file_ids"):
            continue
        setattr(p, field, value)
    _link_items(
        db,
        p.id,
        body.session_ids,
        body.task_ids,
        body.file_ids,
    )
    db.commit()
    db.refresh(p)
    return _to_out(p, db)


@router.delete("/{project_id}", response_model=StatusResponse)
def delete_project(
    project_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StatusResponse:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="project not found")
    db.delete(p)
    db.commit()
    return StatusResponse(detail="deleted")
