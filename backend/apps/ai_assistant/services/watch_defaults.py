"""Alice's defaults check (readme 106 rule 4; Bill, 2026-11-07: "Alice can have maintenance
functions that look for defective values to clean up or ask users to clean up").

The same finder as the sweep (core/services/defaults_sweep): records born without their
model's defaults, values off a default field's list, the profile's unread currency keys.
Alice does not write records here — a blank is a staff member's one command
(sweep_defaults --apply --backup …), a value off its list is the owner's to settle — she
makes one observation per finding, deduplicated, and coaches.

Called by: defaults_watchdog_task (Celery, weekly).
"""
from __future__ import annotations

import logging

from apps.core.services import defaults_sweep

logger = logging.getLogger('alice.defaults')


def _observe(category, model_name, message, detail='', record_id=None, dedup_key='', priority=0):
    from apps.ai_assistant.models.alice import AliceObservation
    if dedup_key and AliceObservation.objects.filter(dedup_key=dedup_key, resolved=False).exists():
        return None
    return AliceObservation.objects.create(category=category, source='alice', priority=priority,
                                          message=message, detail=detail, target_model=model_name,
                                          record_id=record_id, dedup_key=dedup_key)


def check_defaults() -> dict:
    """One observation per finding; the counts for the caller."""
    findings = defaults_sweep.find_all()
    made = 0
    for f in findings:
        if f.kind == 'blank':
            message = f'{f.count} {f.model} record{"s" if f.count != 1 else ""} born without {f.field}'
            detail = (f"The {f.model} definition says {f.field} starts as {f.value!r}. A staff member fills them: "
                      f"manage.py sweep_defaults --apply --backup <pg_dump>. First ids: {f.ids[:10]}.")
            key = f'defaults:blank:{f.model}.{f.field}'
        elif f.kind == 'unlisted':
            message = f"{f.count} {f.model} record{'s' if f.count != 1 else ''} carry {f.field} '{f.value}', which is not on the list"
            detail = (f"Either the value belongs on the {f.model} {f.field} list (a staff member adds it: Cmd+click the "
                      f"field label), or the records take a listed value. First ids: {f.ids[:10]}.")
            key = f'defaults:unlisted:{f.model}.{f.field}:{f.value}'
        else:
            message = 'The company profile prefs.currency carries code, locale and symbol that nothing reads'
            detail = ('Formatting is each definition\'s config.defaults.formatting now (the defaults console). '
                      'sweep_defaults --apply drops the unread keys and keeps the precisions.')
            key = 'defaults:profile:currency'
        if _observe('defaults', f.model, message, detail, record_id=f.ids[0] if f.ids else None,
                    dedup_key=key, priority=1 if f.kind == 'blank' else 0):
            made += 1
    result = {'findings': [f.as_dict() for f in findings], 'observations': made,
              'blank_rows': sum(f.count for f in findings if f.kind == 'blank'),
              'unlisted_rows': sum(f.count for f in findings if f.kind == 'unlisted')}
    logger.info('Defaults check: %s blank rows, %s unlisted rows, %s observations', result['blank_rows'], result['unlisted_rows'], made)
    return result


def run_defaults_watchdog() -> dict:
    return check_defaults()
