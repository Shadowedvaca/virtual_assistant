import re

_WORD_RE = re.compile(r"[^a-z0-9]+", re.IGNORECASE)


def normalize(text: str) -> str:
    return _WORD_RE.sub(" ", text.lower()).strip()


def tokenize(text: str) -> list[str]:
    return [t for t in normalize(text).split() if t]


def split_phrases(text: str) -> list[str]:
    parts = re.split(r",|\band\b", text, flags=re.IGNORECASE)
    cleaned = [" ".join(p.split()).strip(" ,;.-") for p in parts]
    return [p for p in cleaned if len(p) >= 3]
