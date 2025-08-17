from hashlib import sha1


def suggestion_id(seed: str) -> str:
    """Stable short id for a suggestion from a seed string."""
    return sha1(seed.encode("utf-8")).hexdigest()[:12]
