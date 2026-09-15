from __future__ import annotations
from typing import Iterable, Iterator, Optional, Sequence
from django.apps import apps
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from common.refs.links import ensure_bidirectional

OPEN_STATUSES: set[str] = {"open", "pending", "active", "assigned", "todo", "in_progress"}

def _iter_open_actions_for(obj) -> Iterator[object]:
    # 1) Try reverse relation: obj.actions
    if hasattr(obj, "actions"):
        try:
            for a in obj.actions.filter(status__in=OPEN_STATUSES).iterator():
                yield a
            return
        except Exception:
            pass
    # 2) GenericFK fallback: look for plausible Action model(s)
    for candidate in ("support.Action", "actions.Action", "workflow.Action", "tasks.Action"):
        try:
            Model = apps.get_model(candidate)
        except Exception:
            Model = None
        if not Model:
            continue
        try:
            ct = ContentType.objects.get_for_model(obj.__class__)
            qs = Model.objects.filter(content_type=ct, object_id=obj.pk, status__in=OPEN_STATUSES)
            for a in qs.iterator():
                yield a
            return
        except Exception:
            continue

def _iter_assignee_parties(action) -> Iterator[object]:
    # Common direct fields
    for name in ("assignee", "assigned_to", "owner", "contact", "customer", "vendor", "organization", "user"):
        if hasattr(action, name):
            inst = getattr(action, name)
            # Resolve callables (e.g., @property) or GenericForeignKey .get()
            try:
                inst = inst() if callable(inst) else inst
            except Exception:
                pass
            if getattr(inst, "_meta", None) and getattr(inst, "pk", None):
                yield inst
    # Generic assignee via content type/object id
    for prefix in ("assignee", "target", "subject"):
        ct_field = f"{prefix}_content_type"
        id_field = f"{prefix}_object_id"
        if hasattr(action, ct_field) and hasattr(action, id_field):
            try:
                ct = getattr(action, ct_field)
                oid = getattr(action, id_field)
                if ct and oid:
                    Model = ct.model_class()
                    if Model:
                        inst = Model.objects.filter(pk=oid).first()
                        if inst:
                            yield inst
            except Exception:
                continue

@transaction.atomic
def ensure_line_assignee_links(line_obj, *, kind: str = "assignee") -> int:
    """
    Ensure bidirectional refs between the line and each active action's assignee.
    Returns number of links ensured (count of successful upserts).
    """
    created = 0
    for action in _iter_open_actions_for(line_obj):
        for party in _iter_assignee_parties(action):
            if ensure_bidirectional(line_obj, party, kind=kind):
                created += 1
    return created