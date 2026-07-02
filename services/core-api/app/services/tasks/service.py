"""TaskService — CRUD over the Task model with a scheduler hook stub.

TODO(Khoj/APScheduler): wire a real background scheduler and call
``_on_task_scheduled`` to register cron/interval jobs.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.task import Task

logger = get_logger(__name__)


class TaskService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        title: str,
        *,
        description: str | None = None,
        user_id: str | None = None,
        due_at: datetime | None = None,
    ) -> Task:
        task = Task(
            title=title, description=description, user_id=user_id, due_at=due_at
        )
        self._db.add(task)
        self._db.commit()
        self._db.refresh(task)
        self._on_task_scheduled(task)
        return task

    def list(self) -> list[Task]:
        return list(self._db.execute(select(Task)).scalars().all())

    def get(self, task_id: str) -> Task | None:
        return self._db.get(Task, task_id)

    def update(self, task_id: str, **fields: object) -> Task | None:
        task = self._db.get(Task, task_id)
        if not task:
            return None
        due_at_changed = "due_at" in fields and fields["due_at"] != task.due_at
        
        for key, value in fields.items():
            if value is not None and hasattr(task, key):
                setattr(task, key, value)
                
        self._db.commit()
        self._db.refresh(task)
        
        if due_at_changed and task.due_at:
            self._on_task_scheduled(task)
            
        return task

    def delete(self, task_id: str) -> bool:
        task = self._db.get(Task, task_id)
        if not task:
            return False
        self._db.delete(task)
        self._db.commit()
        
        try:
            from app.services.tasks.scheduler import cancel_task_reminder
            cancel_task_reminder(task_id)
        except ImportError:
            pass
            
        return True

    def _on_task_scheduled(self, task: Task) -> None:
        """Scheduler hook to register APScheduler jobs for deadlines."""
        if task.due_at is not None:
            try:
                from app.services.tasks.scheduler import schedule_task_reminder
                schedule_task_reminder(task.id, task.due_at)
            except ImportError:
                logger.debug("Task %s due at %s (APScheduler not installed)", task.id, task.due_at)
