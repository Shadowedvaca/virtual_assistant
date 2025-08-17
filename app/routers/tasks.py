from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud
from ..db import get_session
from ..schemas import TaskCreate, TaskOut, TaskUpdate

router = APIRouter()


@router.post("", response_model=TaskOut)
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_session)):
    return await crud.create_task(db, payload)


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    status: str | None = Query(None, description="Filter by status"),
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
):
    return await crud.list_tasks(db, status=status, limit=limit, offset=offset)


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, db: AsyncSession = Depends(get_session)):
    task = await crud.get_task(db, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(task_id: int, payload: TaskUpdate, db: AsyncSession = Depends(get_session)):
    task = await crud.update_task(db, task_id, payload)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@router.delete("/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_session)):
    ok = await crud.delete_task(db, task_id)
    if not ok:
        raise HTTPException(404, "Task not found")
    return {"deleted": True}
