from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import TaskStatus  # <-- import the enum


class TaskBase(BaseModel):
    # Serialize enums as their values (e.g., "inbox")
    model_config = ConfigDict(use_enum_values=True)

    title: str = Field(..., max_length=280)
    notes: str | None = None
    channel: str | None = None
    due: datetime | None = None
    recurrence: str | None = None
    priority: str | None = None  # P0..P3
    project: str | None = None
    context: list[str] | None = None
    people: list[str] | None = None
    links: list[str] | None = None
    status: TaskStatus = TaskStatus.inbox  # <-- enum type here
    estimated_minutes: int | None = None
    parent_id: int | None = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = None
    notes: str | None = None
    channel: str | None = None
    due: datetime | None = None
    recurrence: str | None = None
    priority: str | None = None
    project: str | None = None
    context: list[str] | None = None
    people: list[str] | None = None
    links: list[str] | None = None
    status: TaskStatus | None = None  # <-- enum (optional)
    estimated_minutes: int | None = None
    parent_id: int | None = None


class TaskOut(TaskBase):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    id: int
    created_at: datetime
    updated_at: datetime
    history: list[dict] | None = None  # <-- add this
