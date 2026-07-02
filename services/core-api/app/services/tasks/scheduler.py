"""Background task scheduler (APScheduler)."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Single global instance of the scheduler
_scheduler: Any = None


def start_scheduler() -> None:
    """Start the APScheduler if SCHEDULER_ENABLED is True."""
    global _scheduler
    if not settings.SCHEDULER_ENABLED:
        logger.info("Scheduler disabled via config (SCHEDULER_ENABLED=False)")
        return

    # Delay import to avoid pulling it in when disabled
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    _scheduler = AsyncIOScheduler()
    
    # Run the task due checker every 60 seconds
    _scheduler.add_job(
        _check_due_tasks,
        trigger=IntervalTrigger(seconds=60),
        id="check_due_tasks",
        replace_existing=True,
    )
    
    _scheduler.start()
    logger.info("Scheduler started successfully")


def shutdown_scheduler() -> None:
    """Shut down the scheduler if it is running."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")
    _scheduler = None


async def _check_due_tasks() -> None:
    """Find pending tasks that are due, mark them 'due', and broadcast."""
    from app.db.session import SessionLocal
    from app.models.task import Task
    from app.ws import manager
    from sqlalchemy import select
    from datetime import datetime
    import pytz

    db = SessionLocal()
    try:
        now = datetime.now(pytz.UTC)
        stmt = (
            select(Task)
            .where(Task.status == "pending")
            .where(Task.due_at <= now)
        )
        due_tasks = db.execute(stmt).scalars().all()
        
        for task in due_tasks:
            task.status = "due"
            logger.info("Task %s is due! Marking status='due'", task.id)
            
            try:
                await manager.broadcast("status", {
                    "type": "task",
                    "id": task.id,
                    "status": "due",
                    "title": task.title,
                })
            except Exception as exc:
                logger.error("Failed to broadcast task %s: %s", task.id, exc)
                
        if due_tasks:
            db.commit()
    except Exception as exc:
        logger.error("Error checking due tasks: %s", exc)
    finally:
        db.close()


def schedule_task_reminder(task_id: str, due_at: datetime) -> None:
    """No-op. Handled by the polling _check_due_tasks job instead."""
    pass


def cancel_task_reminder(task_id: str) -> None:
    """No-op. Handled by the polling _check_due_tasks job instead."""
    pass
