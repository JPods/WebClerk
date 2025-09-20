from __future__ import annotations
from typing import Any, cast
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.apps import apps
from celery import shared_task

from common.refs.actions_index import ensure_action_all_links
from common.refs.policy import PolicyEngine, default_rules
from common.refs.assignees import ensure_line_assignee_links

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def prune_refs_for_owner(self, owner_model: str, owner_id: int) -> int:
    """
    Prunes stale links on a single owner object (e.g., accounts.customer).
    Returns 1 if pruned, 0 if no-op.
    """
    app_label, model_name = owner_model.split(".")
    Model = apps.get_model(app_label, model_name)
    if not Model:
        return 0
    obj = Model.objects.filter(pk=owner_id).first()
    if not obj:
        return 0

    engine = PolicyEngine(default_rules())
    with transaction.atomic():
        mutated = engine.prune_links_for(obj)
        if mutated:
            if hasattr(obj, "refs"):
                obj.save(update_fields=["refs"])
            else:
                obj.save()
        return 1 if mutated else 0

@shared_task
def nightly_prune_refs(owner_model: str = "accounts.customer") -> int:
    """
    Runs during low-load windows via beat scheduler. Iterates candidate owners.
    You can narrow by activity window to keep runtime bounded.
    """
    app_label, model_name = owner_model.split(".")
    Model = apps.get_model(app_label, model_name)
    if not Model:
        return 0

    qs = Model.objects.all().values_list("id", flat=True)
    count = 0
    for owner_id in qs.iterator(chunk_size=500):
        cast(Any, prune_refs_for_owner).delay(owner_model, owner_id)
        count += 1
    return count

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_assignees_for_line(self, line_model: str, line_id: int, kind: str = "assignee") -> int:
    """
    Upserts refs between a line and any active action assignees.
    Safe to call on Action save or Line save.
    """
    app_label, model_name = line_model.split(".")
    Model = apps.get_model(app_label, model_name)
    if not Model:
        return 0
    line = Model.objects.filter(pk=line_id).first()
    if not line:
        return 0
    with transaction.atomic():
        created = ensure_line_assignee_links(line, kind=kind)
        if created:
            line.save(update_fields=["refs"] if hasattr(line, "refs") else None)
        return created

@shared_task
def nightly_backfill_assignee_refs(line_model: str, days: int = 14, kind: str = "assignee") -> int:
    """
    Low-load backfill. Touch lines changed recently and ensure assignee links.
    """
    app_label, model_name = line_model.split(".")
    Model = apps.get_model(app_label, model_name)
    if not Model:
        return 0

    cutoff = timezone.now() - timedelta(days=days)
    qs = Model.objects.all().values_list("id", flat=True)
    # Prefer updated/modified fields when available
    for attr in ("updated_at", "modified_at", "updated", "modified"):
        if attr in [f.name for f in Model._meta.get_fields()]:
            qs = qs.filter(**{f"{attr}__gte": cutoff})
            break

    count = 0
    for line_id in qs.iterator(chunk_size=500):
        cast(Any, sync_assignees_for_line).delay(line_model, line_id, kind=kind)
        count += 1
    return count

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_action_denorm_refs(self, action_model: str, action_id: int) -> int:
    """
    Upserts refs between an Action and all related targets: acts_on, docs, comms, sync, orgs, assignee.
    """
    app_label, model_name = action_model.split(".")
    Model = apps.get_model(app_label, model_name)
    if not Model:
        return 0
    action = Model.objects.filter(pk=action_id).first()
    if not action:
        return 0
    with transaction.atomic():
        created = ensure_action_all_links(action)
        if created and hasattr(action, "refs"):
            action.save(update_fields=["refs"])
        return created

@shared_task
def nightly_backfill_action_refs(action_model: str, days: int = 14) -> int:
    """
    Low-load backfill: ensure Action -> related refs for recently-touched Actions.
    """
    app_label, model_name = action_model.split(".")
    Model = apps.get_model(app_label, model_name)
    if not Model:
        return 0

    cutoff = timezone.now() - timedelta(days=days)
    qs = Model.objects.all().values_list("id", flat=True)
    field_names = {f.name for f in Model._meta.get_fields() if hasattr(f, "name")}
    for attr in ("updated_at", "modified_at", "updated", "modified"):
        if attr in field_names:
            qs = qs.filter(**{f"{attr}__gte": cutoff})
            break

    count = 0
    for act_id in qs.iterator(chunk_size=500):
        cast(Any, sync_action_denorm_refs).delay(action_model, act_id)
        count += 1
    return count