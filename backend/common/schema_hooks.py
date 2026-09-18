import re
from typing import Any

from common.schema_whitelist import WHITELIST


def whitelist_preprocessor(endpoints: list[Any]) -> list[Any]:
    """Filter drf-spectacular endpoints using regex whitelist.

    Accepts the flexible endpoint tuple formats used by drf-spectacular across versions, e.g.:
    - (path, path_regex, method, callback, ...)
    - (path, [(method, callback), ...])  # grouped

    Returns only endpoints whose path matches any pattern in WHITELIST.
    If WHITELIST is empty, exclude all endpoints by default.
    """
    # If nothing is whitelisted, produce an empty schema (opt-in only)
    if not WHITELIST:
        return []

    patterns = [re.compile(p) for p in WHITELIST]

    def allowed(path: str) -> bool:
        return any(p.match(path) for p in patterns)

    filtered: list[Any] = []
    for ep in endpoints:
        # Case 1: flat tuples like (path, path_regex, method, callback, ...)
        if isinstance(ep, tuple) and len(ep) >= 4 and isinstance(ep[0], str):
            path = ep[0]
            if allowed(path):
                filtered.append(ep)
            continue

        # Case 2: grouped by path -> (path, [(method, callback), ...])
        if isinstance(ep, tuple) and len(ep) == 2 and isinstance(ep[0], str):
            path = ep[0]
            if allowed(path):
                filtered.append(ep)
            continue

        # Fallback: attempt attribute-style access or generic sequence
        try:
            path = ep[0] if isinstance(ep, (list, tuple)) and len(ep) > 0 else getattr(ep, 'path', '')
        except Exception:
            path = ''
        if path and allowed(path):
            filtered.append(ep)

    return filtered
