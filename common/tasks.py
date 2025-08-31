from celery import shared_task
from django.apps import apps
from django.utils import timezone

from .models import BaseModel
from .stats_mixin import StatsMixin
from .relationship_stats_mixin import RelationshipStatsMixin

@shared_task(name='common.tasks.refresh_keywords_task')
def refresh_keywords_task(limit: int = 500, batch_size: int = 200):
    """Periodic task to refresh pending keywords across BaseModel subclasses.

    Processes up to 'limit' objects per invocation to avoid long-running tasks.
    """
    processed = 0
    started = timezone.now()
    for model in apps.get_models():
        if not issubclass(model, BaseModel) or model is BaseModel:
            continue
        qs = getattr(model.objects, 'keyword_pending', lambda: None)()
        if qs is None:
            continue
        qs = qs.only('id', 'metadata', 'refs')
        for obj in qs.iterator(chunk_size=batch_size):
            obj.update_keywords()
            model.objects.filter(pk=obj.pk).update(refs=obj.refs, metadata=obj.metadata)
            processed += 1
            if processed >= limit:
                duration = (timezone.now() - started).total_seconds()
                return {'processed': processed, 'duration': duration}
    duration = (timezone.now() - started).total_seconds()
    return {'processed': processed, 'duration': duration}


@shared_task(name='common.tasks.recompute_relationship_counts')
def recompute_relationship_counts(limit: int = 5000, batch_size: int = 500):
    """Recompute denormalized relationship counts for models using RelationshipStatsMixin.

    Strategy:
      - Iterate over RelationshipStatsMixin subclasses (e.g., OrgBase).
      - For each object, derive counts from its relations JSON (if present) or skip if large.
      - Update only when counts actually change to avoid write churn.

    NOTE: This task assumes a 'relations' JSON with keys 'parents','children','linked_ids'.
    Adjust logic when dedicated relationship tables are introduced.
    """
    processed = 0
    updated = 0
    started = timezone.now()
    for model in apps.get_models():
        if not issubclass(model, RelationshipStatsMixin) or model is BaseModel:
            continue
        rel_qs = model.objects.all().only('id', 'relationship_stats')  # type: ignore[attr-defined]
        for obj in rel_qs.iterator(chunk_size=batch_size):
            if processed >= limit:
                duration = (timezone.now() - started).total_seconds()
                return {'processed': processed, 'updated': updated, 'duration': duration}
            processed += 1
            # Heuristic extraction
            relations = getattr(obj, 'relations', None)
            counts = {}
            if isinstance(relations, dict):
                counts['parents'] = len(relations.get('parents', []) or [])
                counts['children'] = len(relations.get('children', []) or [])
                counts['linked'] = len(relations.get('linked_ids', []) or [])
            current = getattr(obj, 'relationship_stats', {}) or {}
            cur_counts = current.get('counts', {}) if isinstance(current, dict) else {}
            if counts and counts != cur_counts:
                obj.set_relation_count('parents', counts['parents'])  # type: ignore[attr-defined]
                obj.set_relation_count('children', counts['children'])  # type: ignore[attr-defined]
                obj.set_relation_count('linked', counts['linked'])  # type: ignore[attr-defined]
                obj.save(update_fields=['relationship_stats'])
                updated += 1
    duration = (timezone.now() - started).total_seconds()
    return {'processed': processed, 'updated': updated, 'duration': duration}


@shared_task(name='common.tasks.recompute_basic_stats')
def recompute_basic_stats(limit: int = 5000, batch_size: int = 500):
    """Example aggregation task to backfill or sanity-sync StatsMixin data.

    Currently placeholder: scans StatsMixin subclasses and ensures required containers
    exist, optionally could recompute derived averages from authoritative sources.
    Extend by injecting domain calculators (e.g., sales totals from transaction lines).
    """
    processed = 0
    normalized = 0
    started = timezone.now()
    for model in apps.get_models():
        if not issubclass(model, StatsMixin) or model is BaseModel:
            continue
        qs = model.objects.all().only('id')  # lean load
        for obj in qs.iterator(chunk_size=batch_size):
            if processed >= limit:
                duration = (timezone.now() - started).total_seconds()
                return {'processed': processed, 'normalized': normalized, 'duration': duration}
            processed += 1
            stats = getattr(obj, 'stats', None)
            changed = False
            if not isinstance(stats, dict):
                stats = {}
                changed = True
            for key in ('counts', 'values', 'series', 'last'):
                if key not in stats:
                    stats[key] = {} if key != 'series' else {}
                    changed = True
            if changed:
                obj.stats = stats  # type: ignore[attr-defined]
                obj.save(update_fields=['stats'])
                normalized += 1
    duration = (timezone.now() - started).total_seconds()
    return {'processed': processed, 'normalized': normalized, 'duration': duration}
