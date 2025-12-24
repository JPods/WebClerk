from __future__ import annotations
from typing import Dict, Any, Iterable, Optional, Tuple
from django.apps import apps
from django.db import transaction
from django.utils import timezone

LINKS_KEY = ("links",)  # canonical: obj.refs["links"]

def _get_links_list(obj) -> list[dict]:
    # Prefer refs.links (canonical)
    refs = getattr(obj, "refs", None)
    if isinstance(refs, dict):
        links = refs.get("links")
        if isinstance(links, list):
            return links
    # Legacy read support: metadata.refs.links
    meta = getattr(obj, "metadata", None) or {}
    if isinstance(meta, dict):
        legacy_refs = meta.get("refs") or {}
        if isinstance(legacy_refs, dict):
            links = legacy_refs.get("links")
            if isinstance(links, list):
                return links
    return []

def _set_links_list(obj, links: list[dict]) -> None:
    # Write to canonical refs.links; fall back to metadata.refs.links if no refs field exists
    if hasattr(obj, "refs"):
        base = getattr(obj, "refs") or {}
        base["links"] = links
        setattr(obj, "refs", base)
    else:
        base = getattr(obj, "metadata", None) or {}
        refs = base.get("refs") or {}
        refs["links"] = links
        base["refs"] = refs
        setattr(obj, "metadata", base)

def _save_refs(obj) -> None:
    if hasattr(obj, "refs"):
        obj.save(update_fields=["refs"])
    elif hasattr(obj, "metadata"):
        obj.save(update_fields=["metadata"])
    else:
        obj.save()

def _link_key(entry: dict) -> Tuple:
    # Uniqueness key (model,id,kind,dir) — ignore ts and other extras
    return (entry.get("model"), entry.get("id"), entry.get("kind"), entry.get("dir"))

def upsert_link(obj, *, to_model: str, to_id: int, kind: str, direction: str) -> bool:
    """
    direction: 'out' for forward (e.g., parent->line), 'in' for reverse (line->parent)
    Returns True if mutated.
    """
    # Support both legacy list-of-links and newer dict-of-buckets formats.
    # If refs.links is a dict of buckets (e.g., {'email': [...]}), upsert into the specific bucket.
    refs = getattr(obj, 'refs', None) or {}
    links_field = refs.get('links') if isinstance(refs, dict) else None
    if isinstance(links_field, dict):
        bucket = links_field.setdefault(to_model.split('.')[-1], [])
        # bucket entries may be dicts or ints; normalize check by id
        for e in bucket:
            if isinstance(e, dict) and e.get('id') == to_id:
                return False
            if isinstance(e, int) and e == to_id:
                return False
        bucket.append(to_id)
        _set_links_list(obj, links_field)
        return True

    # Fallback to legacy list behavior
    links = _get_links_list(obj)
    entry = {"model": to_model, "id": to_id, "kind": kind, "dir": direction, "ts": timezone.now().isoformat()}
    key = _link_key(entry)
    if any(_link_key(e) == key for e in links):
        return False
    links.append(entry)
    _set_links_list(obj, links)
    return True

def remove_link(obj, *, to_model: str, to_id: int, kind: str, direction: str) -> bool:
    refs = getattr(obj, 'refs', None) or {}
    links_field = refs.get('links') if isinstance(refs, dict) else None
    if isinstance(links_field, dict):
        bucket = links_field.get(to_model.split('.')[-1]) or []
        before = len(bucket)
        bucket = [e for e in bucket if not (isinstance(e, int) and e == to_id) and not (isinstance(e, dict) and e.get('id') == to_id)]
        if len(bucket) == before:
            return False
        links_field[to_model.split('.')[-1]] = bucket
        _set_links_list(obj, links_field)
        return True

    links = _get_links_list(obj)
    before = len(links)
    key = (to_model, to_id, kind, direction)
    links = [e for e in links if _link_key(e) != key]
    if len(links) == before:
        return False
    _set_links_list(obj, links)
    return True

@transaction.atomic
def ensure_bidirectional(a, b, *, kind: str) -> bool:
    """
    Ensure a --(kind,out)--> b and b --(kind,in)--> a exist.
    Saves models only if changed. Returns True if any mutation happened.
    """
    a_model = a._meta.label_lower
    b_model = b._meta.label_lower
    changed = False
    if upsert_link(a, to_model=b_model, to_id=b.pk, kind=kind, direction="out"):
        _save_refs(a)
        changed = True
    if upsert_link(b, to_model=a_model, to_id=a.pk, kind=kind, direction="in"):
        _save_refs(b)
        changed = True
    return changed

@transaction.atomic
def remove_bidirectional(a, b, *, kind: str) -> bool:
    a_model = a._meta.label_lower
    b_model = b._meta.label_lower
    changed = False
    if remove_link(a, to_model=b_model, to_id=b.pk, kind=kind, direction="out"):
        _save_refs(a)
        changed = True
    if remove_link(b, to_model=a_model, to_id=a.pk, kind=kind, direction="in"):
        _save_refs(b)
        changed = True
    return changed