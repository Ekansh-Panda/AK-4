"""Task CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.schemas.common import StatusResponse
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate
from app.services.tasks.service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskOut)
def create_task(
    body: TaskCreate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskOut:
    service = TaskService(db)
    task = service.create(
        body.title,
        description=body.description,
        user_id=body.user_id,
        due_at=body.due_at,
    )
    return TaskOut.model_validate(task)


@router.get("", response_model=list[TaskOut])
def list_tasks(user_id: str = Depends(get_current_user), db: Session = Depends(get_db)) -> list[TaskOut]:
    service = TaskService(db)
    return [TaskOut.model_validate(t) for t in service.list()]


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskOut:
    service = TaskService(db)
    task = service.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return TaskOut.model_validate(task)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: str,
    body: TaskUpdate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskOut:
    service = TaskService(db)
    task = service.update(task_id, **body.model_dump(exclude_unset=True))
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return TaskOut.model_validate(task)


@router.delete("/{task_id}", response_model=StatusResponse)
def delete_task(
    task_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StatusResponse:
    service = TaskService(db)
    if not service.delete(task_id):
        raise HTTPException(status_code=404, detail="task not found")
    return StatusResponse(detail="deleted")
