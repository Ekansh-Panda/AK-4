"""Import all models so SQLAlchemy metadata is fully populated."""

from app.models.device import Device
from app.models.file import FileRecord
from app.models.file_chunk import FileChunk
from app.models.memory import Memory
from app.models.message import Message
from app.models.plan import PlanStep, TaskPlan
from app.models.project import Project
from app.models.research import Research
from app.models.session import ChatSession
from app.models.setting import Setting
from app.models.task import Task
from app.models.user import User

__all__ = [
    "ChatSession",
    "Device",
    "FileChunk",
    "FileRecord",
    "Memory",
    "Message",
    "PlanStep",
    "Project",
    "Research",
    "Setting",
    "Task",
    "TaskPlan",
    "User",
]

