from collections import Counter
from collections.abc import Sequence
from math import sqrt


def cosine_similarity(a_tokens: Sequence[str], b_tokens: Sequence[str]) -> float:
    ca, cb = Counter(a_tokens), Counter(b_tokens)
    if not ca or not cb:
        return 0.0
    keys = set(ca) | set(cb)
    dot = sum(ca[k] * cb[k] for k in keys)
    na = sqrt(sum(v * v for v in ca.values()))
    nb = sqrt(sum(v * v for v in cb.values()))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
