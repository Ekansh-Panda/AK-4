"""Projects CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.schemas.common import StatusResponse

router = APIRouter(prefix="/projects", tags=["projects"])


# --- schemas ---
class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    brief: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    brief: str | None = None


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str | None
    status: str
    brief: str | None
    created_at: str | None = None
    updated_at: str | None = None

    model_config = {"from_attributes": True}


def _to_out(p: Project) -> ProjectOut:
    return ProjectOut(
        id=p.id,
        name=p.name,
        description=p.description,
        status=p.status,
        brief=p.brief,
        created_at=str(p.created_at) if p.created_at else None,
        updated_at=str(p.updated_at) if p.updated_at else None,
    )


# --- routes ---
@router.post("", response_model=ProjectOut)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)) -> ProjectOut:
    project = Project(name=body.name, description=body.description, brief=body.brief)
    db.add(project)
    db.commit()
    db.refresh(project)
    return _to_out(project)


@router.get("", response_model=list[ProjectOut])
def list_projects(
    status: str | None = None, db: Session = Depends(get_db)
) -> list[ProjectOut]:
    stmt = select(Project).order_by(Project.created_at.desc())
    if status:
        stmt = stmt.where(Project.status == status)
    rows = db.execute(stmt).scalars().all()
    return [_to_out(r) for r in rows]


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)) -> ProjectOut:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="project not found")
    return _to_out(p)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: str, body: ProjectUpdate, db: Session = Depends(get_db)
) -> ProjectOut:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="project not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    return _to_out(p)


@router.delete("/{project_id}", response_model=StatusResponse)
def delete_project(project_id: str, db: Session = Depends(get_db)) -> StatusResponse:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="project not found")
    db.delete(p)
    db.commit()
    return StatusResponse(detail="deleted")
