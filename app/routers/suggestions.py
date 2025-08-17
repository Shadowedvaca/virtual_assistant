from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud
from ..db import get_session
from ..models import Task, TaskStatus
from ..schemas import TaskCreate
from ..utils.ids import suggestion_id
from ..utils.similarity import cosine_similarity
from ..utils.text import split_phrases, tokenize

router = APIRouter()


class ApplyIn(BaseModel):
    id: str
    type: Literal["combine", "split"]
    task_ids: list[int] | None = None
    task_id: int | None = None
    chosen_subtasks: list[str] | None = None


class CombineSuggestion(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    type: Literal["combine"] = "combine"
    score: float = Field(ge=0.0, le=1.0)
    task_ids: list[int]
    title: str
    rationale: str


class SplitSuggestion(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    type: Literal["split"] = "split"
    score: float = Field(ge=0.0, le=1.0)
    task_id: int
    subtasks: list[str]
    rationale: str


Suggestion = CombineSuggestion | SplitSuggestion  # py311 union


def _build_combine_suggestions(tasks: list[Task], threshold: float, top_k: int) -> list[CombineSuggestion]:
    toks = {t.id: tokenize(t.title or "") for t in tasks}
    pairs: list[tuple[float, Task, Task]] = []
    for i in range(len(tasks)):
        for j in range(i + 1, len(tasks)):
            t1, t2 = tasks[i], tasks[j]
            s = _clamp01(cosine_similarity(toks[t1.id], toks[t2.id]))
            if s >= threshold:
                pairs.append((s, t1, t2))
    pairs.sort(key=lambda x: x[0], reverse=True)

    used: set[int] = set()
    out: list[CombineSuggestion] = []
    for score, t1, t2 in pairs:
        if t1.id in used or t2.id in used:
            continue
        title = t1.title if len(t1.title) <= len(t2.title) else t2.title
        sid = suggestion_id(f"combine|{sorted([t1.id, t2.id])}|{round(score,4)}|{title}")
        out.append(
            CombineSuggestion(
                id=sid,
                score=score,
                task_ids=[t1.id, t2.id],
                title=title,
                rationale=f"High textual similarity between '{t1.title}' and '{t2.title}'.",
            )
        )
        used.add(t1.id)
        used.add(t2.id)
        if len(out) >= top_k:
            break
    return out


def _build_split_suggestions(tasks: list[Task], top_k: int) -> list[SplitSuggestion]:
    out: list[SplitSuggestion] = []
    for t in tasks:
        subs = split_phrases(t.title or "")
        if len(subs) >= 2:
            score = min(0.4 + 0.1 * len(subs), 0.9)
            sid = suggestion_id(f"split|{t.id}|{','.join(subs)}|{round(score,4)}")
            out.append(
                SplitSuggestion(
                    id=sid,
                    score=score,
                    task_id=t.id,
                    subtasks=subs,
                    rationale="Title appears to contain multiple actions (commas/and).",
                )
            )
            if len(out) >= top_k:
                break
    return out


def _clamp01(x: float) -> float:
    # round a bit then clamp for safety
    return max(0.0, min(1.0, round(x, 12)))


def _merge_interleaved(combine: Sequence[Suggestion], split: Sequence[Suggestion], top_k: int) -> list[Suggestion]:
    merged: list[Suggestion] = []
    i = j = 0
    while len(merged) < top_k and (i < len(combine) or j < len(split)):
        if i < len(combine):
            merged.append(combine[i])
            i += 1
        if len(merged) >= top_k:
            break
        if j < len(split):
            merged.append(split[j])
            j += 1
    return merged


def _uniq_union(a: list[str] | None, b: list[str] | None) -> list[str]:
    if not a and not b:
        return []
    a = a or []
    b = b or []
    # preserve order, remove dups
    return list(dict.fromkeys(a + b))


def _better_priority(p: str | None, q: str | None) -> str | None:
    # P0 is highest; keep the better (lower number)
    def score(x):
        if not x:
            return 999
        try:
            return int(x[1:])
        except Exception:
            return 999

    return p if score(p) <= score(q) else q


async def _apply_combine(db: AsyncSession, a_id: int, b_id: int, sid: str) -> dict:
    a = await crud.get_task(db, a_id)
    b = await crud.get_task(db, b_id)
    if not a or not b:
        raise HTTPException(404, "One or both tasks not found")

    # Keep the shorter title as the primary (heuristic mirrors suggestion title)
    primary, secondary = (a, b) if len(a.title or "") <= len(b.title or "") else (b, a)

    # Merge simple fields
    primary.context = _uniq_union(primary.context, secondary.context)
    primary.people = _uniq_union(primary.people, secondary.people)
    primary.links = _uniq_union(primary.links, secondary.links)
    primary.priority = _better_priority(primary.priority, secondary.priority) or primary.priority
    if not primary.project and secondary.project:
        primary.project = secondary.project
    if secondary.due and (not primary.due or secondary.due < primary.due):
        primary.due = secondary.due

    # Notes & history
    merge_note = f"Merged #{secondary.id}: {secondary.title}"
    primary.notes = f"{primary.notes}\n\n{merge_note}" if primary.notes else merge_note

    entry = {
        "event": "suggestion_apply",
        "id": sid,
        "type": "combine",
        "accepted": True,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "merged": [primary.id, secondary.id],
    }
    for t in (primary, secondary):
        hist = t.history or []
        hist.append(entry)
        t.history = hist

    # Mark secondary done and point it to primary for traceability
    secondary.status = TaskStatus.done
    secondary.parent_id = primary.id

    await db.commit()
    await db.refresh(primary)
    await db.refresh(secondary)
    return {"primary_id": primary.id, "secondary_id": secondary.id}


async def _apply_split(db: AsyncSession, task_id: int, subtasks: list[str], sid: str) -> dict:
    parent = await crud.get_task(db, task_id)
    if not parent:
        raise HTTPException(404, "Task not found")

    if not subtasks:
        raise HTTPException(400, "No subtasks provided")

    created_ids: list[int] = []
    for title in subtasks:
        child = TaskCreate(
            title=title,
            notes=None,
            channel=parent.channel,
            due=parent.due,
            recurrence=None,
            priority=parent.priority,
            project=parent.project,
            context=parent.context,
            people=parent.people,
            links=parent.links,
            status=TaskStatus.inbox,  # if schemas.TaskCreate expects TaskStatus
            estimated_minutes=None,
            parent_id=parent.id,
        )
        t = await crud.create_task(db, child)
        created_ids.append(t.id)

    # History on parent
    entry = {
        "event": "suggestion_apply",
        "id": sid,
        "type": "split",
        "accepted": True,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "children": created_ids,
    }
    hist = parent.history or []
    hist.append(entry)
    parent.history = hist

    await db.commit()
    await db.refresh(parent)
    return {"parent_id": parent.id, "children": created_ids}


@router.get("", response_model=list[Suggestion])
async def get_suggestions(
    threshold: float = Query(0.45, ge=0.0, le=1.0, description="Cosine similarity threshold for combine suggestions"),
    top_k: int = Query(5, ge=1, le=20),
    include_split: bool = Query(True),
    db: AsyncSession = Depends(get_session),
) -> list[Suggestion]:
    tasks = await crud.list_tasks(db, status=None, limit=200, offset=0)
    combine = _build_combine_suggestions(tasks, threshold=threshold, top_k=top_k)
    split = _build_split_suggestions(tasks, top_k=top_k) if include_split else []
    # OLD:
    # merged: List[Suggestion] = sorted([*combine, *split], key=lambda s: s.score, reverse=True)
    # return merged[:top_k]
    # NEW:
    return _merge_interleaved(combine, split, top_k)


class FeedbackIn(BaseModel):
    """Minimal feedback payload referencing a suggestion by id."""

    id: str
    type: Literal["combine", "split"]
    accepted: bool
    # For combine: IDs the suggestion referenced
    task_ids: list[int] | None = None
    # For split: source task id (and optional chosen subtasks)
    task_id: int | None = None
    chosen_subtasks: list[str] | None = None
    reason: str | None = None


@router.post("/feedback")
async def submit_feedback(payload: FeedbackIn, db: AsyncSession = Depends(get_session)):
    """Record user feedback about a suggestion into related tasks' history."""
    now = datetime.now(UTC).isoformat()
    entry = {
        "event": "suggestion_feedback",
        "id": payload.id,
        "type": payload.type,
        "accepted": payload.accepted,
        "reason": payload.reason,
        "chosen_subtasks": payload.chosen_subtasks,
        "timestamp": now,
    }

    touched: list[int] = []
    if payload.type == "combine" and payload.task_ids:
        for tid in payload.task_ids:
            task = await crud.get_task(db, tid)
            if not task:
                continue
            hist = task.history or []
            hist.append(entry)
            task.history = hist
            touched.append(tid)
    elif payload.type == "split" and payload.task_id is not None:
        task = await crud.get_task(db, payload.task_id)
        if task:
            hist = task.history or []
            hist.append(entry)
            task.history = hist
            touched.append(payload.task_id)

    if touched:
        await db.commit()

    return {"ok": True, "touched": touched}


@router.post("/apply")
async def apply_suggestion(payload: ApplyIn, db: AsyncSession = Depends(get_session)):
    if payload.type == "combine":
        if not payload.task_ids or len(payload.task_ids) != 2:
            raise HTTPException(400, "combine requires exactly two task_ids")
        result = await _apply_combine(db, payload.task_ids[0], payload.task_ids[1], payload.id)
        return {"ok": True, "result": result}

    if payload.type == "split":
        subs = (payload.chosen_subtasks or []).copy()
        if not subs and payload.task_id is not None:
            # fall back to what the suggestion proposed by recomputing once (optional)
            pass
        if payload.task_id is None:
            raise HTTPException(400, "split requires task_id")
        result = await _apply_split(db, payload.task_id, subs, payload.id)
        return {"ok": True, "result": result}

    raise HTTPException(400, "Unknown suggestion type")
