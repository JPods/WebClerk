"""A model's definition — its wc:model Setting — read one part at a time.

Each server process keeps what it has read, and re-checks a part's fingerprint (an md5 of
that part, computed in the database) at most REVALIDATE_S after it last looked: a change made
in another process, or by a migration, is seen within a second without a restart (Setting
audit S-4, 2026-10-28). Access (config.access) and purpose lists (config.selectlists.purpose)
are both read here.
"""
from __future__ import annotations

import json
import time
from typing import Any, Callable, Optional

#: (model key, path) -> (fingerprint, when last checked, built value)
_cache: dict[tuple[str, tuple[str, ...]], tuple[str, float, Any]] = {}
REVALIDATE_S = 1.0

_SQL = ("SELECT md5(coalesce(config #> %s, 'null'::jsonb)::text), {value} FROM settings "
        "WHERE purpose = 'wc:model' AND parent_model = %s ORDER BY id LIMIT 1")


def part(key: str, path: tuple[str, ...], build: Callable[[Any], Any]) -> Any:
    """build(config at path) for model `key`; build receives None when the model has no
    definition or the definition has no such part."""
    from django.db import connection
    now = time.monotonic()
    hit = _cache.get((key, path))
    if hit and now - hit[1] < REVALIDATE_S:
        return hit[2]
    with connection.cursor() as cur:
        cur.execute(_SQL.format(value="''"), [list(path), key])
        row = cur.fetchone()
        fingerprint = row[0] if row else ''
        if hit and hit[0] == fingerprint:
            value = hit[2]
        else:
            cur.execute(_SQL.format(value='config #> %s'), [list(path), list(path), key])
            row = cur.fetchone()
            raw = row[1] if row else None
            value = build(json.loads(raw) if isinstance(raw, str) else raw)
    _cache[(key, path)] = (fingerprint, now, value)
    return value


def clear(key: Optional[str] = None) -> None:
    """Forget what this process read: one model's parts, or every model's."""
    for cached in [k for k in _cache if key is None or k[0] == key]:
        _cache.pop(cached, None)


def may_change(actor) -> bool:
    """A definition's lists and layouts are changed by a login flagged is_staff, or by the code
    (Bill, 2026-10-29)."""
    from apps.core.services.door import as_actor
    actor = as_actor(actor)
    if not actor.is_guarded:
        return True
    return bool(actor.user is not None and getattr(actor.user, 'is_staff', False))


#: The field a list's From/To period filters when the definition names none: when the record
#: was made.
DEFAULT_PERIOD_FIELD = 'dt_created'


def period_field(key: str) -> str:
    """The field that dates a record of model ``key`` for a period (From/To on its list):
    config.period_field in its definition, else dt_created. A GL row's period is its document's
    date, dt_document, not the day it posted (Bill, 2026-11-27). A name the model does not have as
    an integer dt_ field (UTC epoch ms) is ignored for the default, so a typo never filters nothing."""
    from django.db import models as dj_models
    from apps.core.utils.registry import resolve
    declared = part(key, ('period_field',), lambda v: v if isinstance(v, str) else '')
    if not declared or not declared.startswith('dt_'):
        return DEFAULT_PERIOD_FIELD
    ModelCls = resolve(key)
    try:
        field = ModelCls._meta.get_field(declared) if ModelCls else None
    except Exception:
        field = None
    return declared if isinstance(field, dj_models.BigIntegerField) else DEFAULT_PERIOD_FIELD
