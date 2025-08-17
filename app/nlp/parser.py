from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from dateparser.search import search_dates

# Simple patterns for inline tags
PRIORITY_PAT = re.compile(r"\b(p[0-3])\b", re.IGNORECASE)
PROJECT_PAT = re.compile(r"#([\w\-]+)")
CONTEXT_PAT = re.compile(r"@([\w\-]+)")
PEOPLE_PAT = re.compile(r"\+([\w\-]+)")

PHOENIX_TZ = ZoneInfo("America/Phoenix")
DATE_SETTINGS = {
    "PREFER_DATES_FROM": "future",
    "RELATIVE_BASE": datetime.now(PHOENIX_TZ),
    "RETURN_AS_TIMEZONE_AWARE": True,
    "TIMEZONE": "America/Phoenix",
    "DATE_ORDER": "MDY",
}


def _extract_due(text: str):
    """
    Find a date/time phrase anywhere in the text.
    Returns (due_datetime, cleaned_text).
    """
    matches = search_dates(text, settings=DATE_SETTINGS, languages=["en"])
    if not matches:
        return None, text

    # Take the last match (usually the most specific at the end of the sentence)
    matched_phrase, dt = matches[-1]

    # Remove just the last occurrence of that phrase from the text
    idx = text.rfind(matched_phrase)
    if idx != -1:
        cleaned = text[:idx] + text[idx + len(matched_phrase) :]
    else:
        cleaned = text  # fallback; shouldn't happen often

    return dt, cleaned


def parse_quick_task(text: str) -> dict:
    """
    Lightweight parser:
    - due date via search_dates (e.g., 'tomorrow 4pm', 'next Fri', 'Aug 20 5p')
    - priority p0..p3
    - project via #tag, context via @tag, people via +name
    - strips tags/date from title; keeps the rest as the title
    """
    original = text.strip()
    work = original

    # priority
    pr_match = PRIORITY_PAT.search(work)
    priority = pr_match.group(1).upper() if pr_match else None
    if pr_match:
        work = work[: pr_match.start()] + work[pr_match.end() :]

    # project, context, people (can be multiple)
    projects = PROJECT_PAT.findall(work)
    contexts = CONTEXT_PAT.findall(work)
    people = PEOPLE_PAT.findall(work)
    work = PROJECT_PAT.sub("", work)
    work = CONTEXT_PAT.sub("", work)
    work = PEOPLE_PAT.sub("", work)

    # due date (search inside the remaining text)
    due, work = _extract_due(work)

    # final title cleanup
    title = " ".join(work.split()).strip(",;") or original

    return {
        "title": title,
        "notes": None,
        "due": due,  # timezone-aware datetime in America/Phoenix
        "priority": priority,
        "project": projects[0] if projects else None,
        "context": contexts or None,
        "people": people or None,
        "links": None,
    }
