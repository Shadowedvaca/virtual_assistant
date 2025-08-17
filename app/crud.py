from datetime import UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Task, TaskStatus
from .schemas import TaskCreate, TaskUpdate


def _normalize_due(dt):
    if dt is None:
        return None
    # If tz-aware, convert to UTC and drop tzinfo (store naive UTC)
    if getattr(dt, "tzinfo", None) is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


async def create_task(db: AsyncSession, payload: TaskCreate) -> Task:
    data = payload.model_dump()
    data["due"] = _normalize_due(data.get("due"))
    task = Task(**data)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def get_task(db: AsyncSession, task_id: int) -> Task | None:
    res = await db.execute(select(Task).where(Task.id == task_id))
    return res.scalar_one_or_none()


async def list_tasks(db: AsyncSession, status: str | None = None, limit: int = 100, offset: int = 0) -> list[Task]:
    stmt = select(Task).order_by(Task.created_at.desc())
    if status:
        stmt = stmt.where(Task.status == TaskStatus(status))
    stmt = stmt.limit(limit).offset(offset)
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def update_task(db: AsyncSession, task_id: int, payload: TaskUpdate):
    task = await get_task(db, task_id)
    if not task:
        return None
    updates = payload.model_dump(exclude_unset=True)
    if "due" in updates:
        updates["due"] = _normalize_due(updates["due"])
    for k, v in updates.items():
        setattr(task, k, v)
    await db.commit()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task_id: int) -> bool:
    task = await get_task(db, task_id)
    if not task:
        return False
    await db.delete(task)
    await db.commit()
    return True
