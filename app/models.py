import enum
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class TaskStatus(str, enum.Enum):
    inbox = "inbox"
    planned = "planned"
    in_progress = "in_progress"
    done = "done"
    delegated = "delegated"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(280), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    channel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    due: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    recurrence: Mapped[str | None] = mapped_column(String(255), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(10), nullable=True)
    project: Mapped[str | None] = mapped_column(String(120), nullable=True)
    context: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    people: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    links: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.inbox, nullable=False)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tasks.id"), nullable=True)
    ai_suggestions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    history: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
