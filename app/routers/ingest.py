from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud import create_task
from ..db import get_session
from ..nlp.parser import parse_quick_task
from ..schemas import TaskCreate, TaskOut

router = APIRouter()


class IngestIn(BaseModel):
    text: str
    channel: str | None = None
    links: list[str] | None = None


@router.post("", response_model=TaskOut)
async def ingest(payload: IngestIn, db: AsyncSession = Depends(get_session)):
    parsed = parse_quick_task(payload.text)
    task = TaskCreate(
        title=parsed["title"],
        notes=parsed.get("notes"),
        due=parsed.get("due"),
        priority=parsed.get("priority"),
        project=parsed.get("project"),
        context=parsed.get("context"),
        people=parsed.get("people"),
        links=payload.links or parsed.get("links"),
        channel=payload.channel or "api",
        # status default applies (inbox)
    )
    return await create_task(db, task)
