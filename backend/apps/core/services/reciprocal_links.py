"""Two-sided links (Bill, 2026-10-31): "any and all models can be related to each other via
.refs.links". When a record lists another in ``refs.links.<model>[]``, that record lists it back
in its own ``refs.links.<this model>[]``. The save door writes both sides in one unit of work, so
they cannot disagree; deleting either side takes it off the other.

A link is a list of ``{id, …}`` under a key that names a model with a ``refs`` field. Anything
else under refs.links — an action's Gantt ``children``/``parents``, a transaction's customer
snapshot object, a ledger's ``org``/``parent`` — is not a two-sided link and is left as it is.

A side the door writes on another record bumps that record's version, so a form holding it
reloads before saving rather than writing back a list without the new link.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional, Set

from django.db.models import F

logger = logging.getLogger('console')


def _ids(refs, key: str) -> Set[int]:
    links = refs.get('links') if isinstance(refs, dict) else None
    rows = links.get(key) if isinstance(links, dict) else None
    out: Set[int] = set()
    if not isinstance(rows, list):
        return out
    for row in rows:
        raw = row.get('id') if isinstance(row, dict) else row
        try:
            out.add(int(raw))
        except (TypeError, ValueError):
            continue
    return out


def _keys(refs) -> Set[str]:
    links = refs.get('links') if isinstance(refs, dict) else None
    return set(links) if isinstance(links, dict) else set()


@lru_cache(maxsize=None)
def _linkable(key: str):
    """The model a link key names, when it can list links back (it has refs); else None."""
    from apps.core.services.door import resolve_model
    try:
        model_cls, model_key, _ = resolve_model(key)
    except Exception:  # noqa: BLE001 - a key that is not a model has no other side
        return None
    if model_key != key or not any(f.name == 'refs' for f in model_cls._meta.concrete_fields):
        return None
    return model_cls


def _set_side(model_cls, pk: int, key: str, other_id: int, present: bool) -> None:
    """Add or remove ``{id: other_id}`` in that record's refs.links.<key>, version bumped."""
    row = model_cls.objects.filter(pk=pk).values('refs').first()
    if row is None:
        return
    refs = row['refs'] if isinstance(row['refs'], dict) else {}
    links = refs.get('links') if isinstance(refs.get('links'), dict) else {}
    current = links.get(key)
    if current is not None and not isinstance(current, list):
        logger.warning("[LINKS] %s #%s refs.links.%s is not a list; left as it is", model_cls.__name__, pk, key)
        return
    current = [r for r in (current or []) if isinstance(r, dict)]
    has = any(str(r.get('id')) == str(other_id) for r in current)
    if present == has:
        return
    current = current + [{'id': other_id}] if present else [r for r in current if str(r.get('id')) != str(other_id)]
    update = {'refs': {**refs, 'links': {**links, key: current}}}
    if any(f.name == 'version' for f in model_cls._meta.concrete_fields):
        update['version'] = F('version') + 1
    model_cls.objects.filter(pk=pk).update(**update)


def keep(model_key: str, before_refs, obj) -> None:
    """After ``obj`` (of ``model_key``) saved: write the other side of what its links changed."""
    after_refs = getattr(obj, 'refs', None)
    if before_refs == after_refs or _linkable(model_key) is None:
        return
    for other_key in _keys(before_refs) | _keys(after_refs):
        old, new = _ids(before_refs, other_key), _ids(after_refs, other_key)
        if old == new:
            continue
        other_cls = _linkable(other_key)
        if other_cls is None:
            continue
        for pk in new - old:
            if not (other_key == model_key and pk == obj.pk):
                _set_side(other_cls, pk, model_key, obj.pk, True)
        for pk in old - new:
            _set_side(other_cls, pk, model_key, obj.pk, False)


def forget(model_key: str, obj) -> None:
    """``obj`` is being deleted: the records it is linked with no longer list it."""
    refs = getattr(obj, 'refs', None)
    if _linkable(model_key) is None:
        return
    for other_key in _keys(refs):
        other_cls = _linkable(other_key)
        if other_cls is None:
            continue
        for pk in _ids(refs, other_key):
            _set_side(other_cls, pk, model_key, obj.pk, False)
