"""Task management tool."""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.services.tasks.service import TaskService
from app.services.tools.base import Tool

logger = get_logger(__name__)


class TaskTool(Tool):
    name = "manage_tasks"
    description = "List, create, or complete background tasks and reminders."

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "create", "complete"],
                    "description": "The action to perform."
                },
                "title": {
                    "type": "string",
                    "description": "Title of the task (required for create)."
                },
                "description": {
                    "type": "string",
                    "description": "Optional description for the task."
                },
                "task_id": {
                    "type": "string",
                    "description": "ID of the task (required for complete)."
                }
            },
            "required": ["action"]
        }

    def run(self, **kwargs: Any) -> Any:
        action = kwargs.get("action")
        
        with SessionLocal() as db:
            service = TaskService(db)
            
            if action == "list":
                tasks = service.list()
                return [
                    {
                        "id": t.id,
                        "title": t.title,
                        "description": t.description,
                        "status": t.status,
                        "created_at": t.created_at.isoformat() if t.created_at else None
                    }
                    for t in tasks
                ]
            
            elif action == "create":
                title = kwargs.get("title")
                if not title:
                    return {"error": "title is required for create"}
                desc = kwargs.get("description", "")
                t = service.create(title=title, description=desc)
                return {"id": t.id, "title": t.title, "status": t.status}
                
            elif action == "complete":
                task_id = kwargs.get("task_id")
                if not task_id:
                    return {"error": "task_id is required for complete"}
                t = service.update(task_id, status="completed")
                if not t:
                    return {"error": "task not found"}
                return {"id": t.id, "status": t.status}
                
            else:
                return {"error": f"Unknown action: {action}"}
