"""
Alice Select List Watchdog — Detect hallucinated options and unlisted values.

During the first months of a new database, users enter real data that either
matches or contradicts the seeded select list baselines. This watchdog:

1. Finds UNLISTED values — data in DB that has no matching select option.
   These are real-world values the baseline missed. Alice recommends adding them.

2. Finds UNUSED options — options defined but never used by any record.
   After 30+ days and 50+ records, unused options are hallucination candidates.
   Alice recommends user review.

3. Tracks COVERAGE — what % of defined options are actually used.
   Low coverage on a field with many records = the baseline was wrong.

Creates AliceObservation records for user review. The user adds/removes options
via Cmd+click on field labels. Alice learns from their choices.

Called by: select_list_watchdog_task (Celery, weekly)
"""
from __future__ import annotations

import logging
import time

from apps.core.constants.model_registry import MODEL_REGISTRY, get_model_meta
from apps.core.services.field_behaviors import get_field_behaviors, get_model_field_map

logger = logging.getLogger('alice.select_lists')

# Minimum thresholds before flagging — don't flag empty databases
MIN_RECORDS_FOR_UNUSED = 50    # need enough records before "unused" means anything
MIN_DAYS_FOR_UNUSED = 30       # wait 30 days before flagging unused options
MIN_RECORDS_FOR_UNLISTED = 5   # any model with 5+ records can have unlisted values


def _create_observation(category, model_name, message, detail='',
                        record_id=None, dedup_key='', priority=0):
    from apps.ai_assistant.models.alice import AliceObservation
    if dedup_key:
        if AliceObservation.objects.filter(dedup_key=dedup_key, resolved=False).exists():
            return None
    return AliceObservation.objects.create(
        category=category, source='alice', priority=priority,
        message=message, detail=detail,
        model_name=model_name, record_id=record_id, dedup_key=dedup_key,
    )


def _get_db_age_days():
    """Estimate database age from the oldest active record's dt_created."""
    try:
        from apps.core.models.setting import Setting
        oldest = Setting.objects.filter(is_active=True).order_by('dt_created').first()
        if oldest and oldest.dt_created:
            age_ms = int(time.time() * 1000) - oldest.dt_created
            return max(0, age_ms // (1000 * 86400))
    except Exception:
        pass
    return 0


def check_unlisted_values(limit: int = 500) -> dict:
    """Find values stored in DB that have no matching select option.

    These are real-world values the user entered. Alice recommends
    adding them to the select list so future users see them as options.
    """
    observations = 0
    fields_checked = 0
    unlisted_details = []

    for model_key, meta in sorted(MODEL_REGISTRY.items()):
        field_map = get_model_field_map(model_key)
        if not field_map:
            continue

        try:
            model_cls = meta.import_model()
        except Exception:
            continue

        record_count = model_cls.objects.filter(is_active=True).count()
        if record_count < MIN_RECORDS_FOR_UNLISTED:
            continue

        computed = get_field_behaviors(model_key, field_map)

        for field_name, behavior in computed.items():
            if behavior.get('type') != 'select' or '.' in field_name:
                continue
            opts = behavior.get('options', [])
            if not opts:
                continue

            try:
                model_cls._meta.get_field(field_name)
            except Exception:
                continue

            fields_checked += 1
            defined_values = {o['value'] for o in opts if o.get('value')}

            try:
                actual = set(
                    model_cls.objects.filter(is_active=True)
                    .exclude(**{field_name: ''})
                    .exclude(**{f'{field_name}__isnull': True})
                    .values_list(field_name, flat=True)
                    .distinct()[:limit]
                )
            except Exception:
                continue

            unlisted = actual - defined_values
            if unlisted:
                # Count how many records use unlisted values
                try:
                    unlisted_count = model_cls.objects.filter(
                        is_active=True,
                        **{f'{field_name}__in': list(unlisted)},
                    ).count()
                except Exception:
                    unlisted_count = len(unlisted)

                detail_text = (
                    f"{len(unlisted)} value(s) in {model_key}.{field_name} "
                    f"not in select options: {sorted(unlisted)[:10]}. "
                    f"{unlisted_count} records use these values. "
                    f"Cmd+click the '{field_name}' label to add them."
                )
                dedup = f"select_unlisted_{model_key}_{field_name}"
                obs = _create_observation(
                    category='anomaly',
                    model_name=model_key,
                    message=f"Unlisted {field_name} values on {model_key}: {sorted(unlisted)[:3]}",
                    detail=detail_text,
                    dedup_key=dedup,
                    priority=0,
                )
                if obs:
                    observations += 1
                unlisted_details.append({
                    'model': model_key, 'field': field_name,
                    'unlisted': sorted(unlisted), 'record_count': unlisted_count,
                })

    return {
        'observations': observations,
        'fields_checked': fields_checked,
        'unlisted_fields': len(unlisted_details),
        'details': unlisted_details,
    }


def check_unused_options(limit: int = 500) -> dict:
    """Find defined options that no record uses.

    Only flags after MIN_DAYS_FOR_UNUSED and MIN_RECORDS_FOR_UNUSED.
    Unused options after real usage = hallucination candidate.
    Alice recommends user review — keep, rename, or remove.
    """
    db_age_days = _get_db_age_days()
    if db_age_days < MIN_DAYS_FOR_UNUSED:
        return {
            'observations': 0, 'skipped': True,
            'reason': f'Database is {db_age_days} days old (need {MIN_DAYS_FOR_UNUSED})',
        }

    observations = 0
    fields_checked = 0
    unused_details = []

    for model_key, meta in sorted(MODEL_REGISTRY.items()):
        field_map = get_model_field_map(model_key)
        if not field_map:
            continue

        try:
            model_cls = meta.import_model()
        except Exception:
            continue

        record_count = model_cls.objects.filter(is_active=True).count()
        if record_count < MIN_RECORDS_FOR_UNUSED:
            continue

        computed = get_field_behaviors(model_key, field_map)

        for field_name, behavior in computed.items():
            if behavior.get('type') != 'select' or '.' in field_name:
                continue
            opts = behavior.get('options', [])
            if not opts:
                continue

            try:
                model_cls._meta.get_field(field_name)
            except Exception:
                continue

            fields_checked += 1
            defined_values = {o['value'] for o in opts if o.get('value')}

            try:
                actual = set(
                    model_cls.objects.filter(is_active=True)
                    .exclude(**{field_name: ''})
                    .exclude(**{f'{field_name}__isnull': True})
                    .values_list(field_name, flat=True)
                    .distinct()[:limit]
                )
            except Exception:
                continue

            unused = defined_values - actual
            if unused and len(unused) < len(defined_values):
                # Don't flag if ALL are unused (empty DB for this field)
                detail_text = (
                    f"{len(unused)}/{len(defined_values)} options for "
                    f"{model_key}.{field_name} have never been used "
                    f"({record_count} records, {db_age_days} days): "
                    f"{sorted(unused)[:10]}. "
                    f"Review: Cmd+click '{field_name}' label to edit options."
                )
                dedup = f"select_unused_{model_key}_{field_name}"
                obs = _create_observation(
                    category='coaching',
                    model_name=model_key,
                    message=f"Unused {field_name} options on {model_key}: {sorted(unused)[:3]}",
                    detail=detail_text,
                    dedup_key=dedup,
                    priority=0,
                )
                if obs:
                    observations += 1
                unused_details.append({
                    'model': model_key, 'field': field_name,
                    'unused': sorted(unused),
                    'total_defined': len(defined_values),
                    'record_count': record_count,
                })

    return {
        'observations': observations,
        'fields_checked': fields_checked,
        'unused_fields': len(unused_details),
        'db_age_days': db_age_days,
        'details': unused_details,
    }


def check_coverage(limit: int = 500) -> dict:
    """Report coverage stats for all select fields.

    Coverage = % of defined options that appear in at least one record.
    Low coverage + many records = baseline was wrong for this business.
    """
    stats = []

    for model_key, meta in sorted(MODEL_REGISTRY.items()):
        field_map = get_model_field_map(model_key)
        if not field_map:
            continue

        try:
            model_cls = meta.import_model()
        except Exception:
            continue

        record_count = model_cls.objects.filter(is_active=True).count()
        if record_count < MIN_RECORDS_FOR_UNLISTED:
            continue

        computed = get_field_behaviors(model_key, field_map)

        for field_name, behavior in computed.items():
            if behavior.get('type') != 'select' or '.' in field_name:
                continue
            opts = behavior.get('options', [])
            if not opts:
                continue

            try:
                model_cls._meta.get_field(field_name)
            except Exception:
                continue

            defined_values = {o['value'] for o in opts if o.get('value')}

            try:
                actual = set(
                    model_cls.objects.filter(is_active=True)
                    .exclude(**{field_name: ''})
                    .exclude(**{f'{field_name}__isnull': True})
                    .values_list(field_name, flat=True)
                    .distinct()[:limit]
                )
            except Exception:
                continue

            used = defined_values & actual
            coverage = (len(used) / len(defined_values) * 100) if defined_values else 0

            stats.append({
                'model': model_key,
                'field': field_name,
                'defined': len(defined_values),
                'used': len(used),
                'coverage': round(coverage, 1),
                'records': record_count,
            })

    return {'fields': len(stats), 'stats': stats}


def run_select_list_watchdog(limit: int = 500) -> dict:
    """Run all select list reality checks. Called by Celery weekly."""
    results = {}
    results['unlisted'] = check_unlisted_values(limit)
    results['unused'] = check_unused_options(limit)
    results['coverage'] = check_coverage(limit)

    total_obs = (
        results['unlisted'].get('observations', 0) +
        results['unused'].get('observations', 0)
    )
    logger.info(
        "Select list watchdog complete: %d observations, %d unlisted fields, %d unused fields",
        total_obs,
        results['unlisted'].get('unlisted_fields', 0),
        results['unused'].get('unused_fields', 0),
    )
    return results
