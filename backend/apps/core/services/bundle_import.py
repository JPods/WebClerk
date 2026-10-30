"""Importing a bundle keeps one record of it (Bill, 2026-10-29).

Every bundle loaded into this installation — the init set, a settings bundle, from WC_HQ, the
shipped copy or a file someone uploads — becomes:

    a Bundle row     sync_bundle, purpose bundle_import: status pending → completed | defects,
                     response = {source, counts, defects}
    its file         WORK_DIR/bundles/general/incoming/<status>/<bundle id>.json, moved with
                     the status, so the folder a bundle sits in says where it stands
    one Log row      audit / bundle_import, pointing at the Bundle row

The Bundle row's status is the flag: a record the import refused is not logged one by one, the
defects list on the row is the detail. Once they are resolved, rerun(bundle_id) loads the same
file again. Alice looks each day (escalate): defects still unresolved after ESCALATE_DAYS
become one Action to the system administrator (company profile config.system_admin).
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

PURPOSE = 'bundle_import'
DEFECTS_PURPOSE = 'bundle_defects'
SHOWN = 20                       # defects written into the Action; the Bundle row has them all
ESCALATE_DAYS = 3                # a bundle left in defects this long becomes an Action


def _loaders() -> dict[str, Callable[..., dict]]:
    """recommended: a set authored at WC_HQ — settings, chart and reports (init, gls, reports,
    settings). settings: a settings file someone supplies, merged or replaced."""
    from apps.core.services.installation_init import load_bundle
    from apps.core.services.setting_bootstrap import import_settings_bundle
    return {'recommended': load_bundle, 'settings': import_settings_bundle}


def run(name: str, bundle: dict | list, *, source: str, load: str = 'recommended',
        **options) -> dict[str, Any]:
    """Load bundle `name` with loader `load` and keep the record of it. Returns the loader's
    result with bundle_id. options go to the loader (force_replace, …)."""
    from apps.core.services.alice_connections import ensure_hq_connection
    from apps.sync.models.bundle import Bundle
    if load not in _loaders():
        raise ValueError(f'a bundle loads as one of {", ".join(_loaders())}, not {load!r}')
    record = Bundle.objects.create(
        connection=ensure_hq_connection(), direction='pull', purpose=PURPOSE,
        model_name=f'bundle_{name}', status='pending',
        size=len(json.dumps(bundle, default=str)),
        config={'source': source, 'load': load, 'options': options},
    )
    record.save_payload_to_disk(bundle)
    return _load(record, bundle)


def rerun(bundle_id: int) -> dict[str, Any]:
    """Load a bundle already recorded again — after its defects are resolved."""
    from apps.sync.models.bundle import Bundle
    record = Bundle.objects.get(pk=bundle_id, purpose=PURPOSE)
    bundle = record.get_payload()
    if bundle is None:
        raise ValueError(f'bundle {bundle_id} has no file to load')
    return _load(record, bundle)


def _load(record, bundle) -> dict[str, Any]:
    from apps.core.models.log import Log
    name = record.model_name.removeprefix('bundle_')
    config = dict(record.config or {})
    started = time.monotonic()
    try:
        result = _loaders()[config['load']](bundle, **(config.get('options') or {}))
    except Exception as exc:                       # recorded as the defect it is, then raised
        result = {'errors': [f'the import stopped: {type(exc).__name__}: {exc}']}
        _close(record, config, result, started, name)
        raise
    _close(record, config, result, started, name)
    logger.info('bundle_import %s #%s: %s, %d defect(s)', name, record.pk, record.status,
                len(result.get('errors') or []))
    Log.write('audit', PURPOSE, model_name='sync_bundle', record_id=record.pk,
              name=record.model_name,
              details={'status': record.status, **(record.response or {}),
                       'defects': len(result.get('errors') or [])})
    return {**result, 'bundle_id': record.pk}


def _close(record, config, result, started, name) -> None:
    from apps.sync.services import bundle_storage
    defects = list(result.get('errors') or [])
    record.status = 'defects' if defects else 'completed'
    path = bundle_storage.move(record.pk, record.model_name, record.direction, record.status)
    if path:
        config['payload_path'] = path
    record.config = config
    record.response = {'source': config.get('source'),
                       'counts': {k: v for k, v in result.items() if k != 'errors'},
                       'defects': defects}
    record.dt_processed = int(time.time() * 1000)
    record.duration = int((time.monotonic() - started) * 1000)
    record.save(update_fields=['status', 'config', 'response', 'dt_processed', 'duration',
                               'dt_modified', 'version'])


def escalate(*, now_ms: int | None = None) -> list[int]:
    """Alice, daily: each bundle still in defects ESCALATE_DAYS after it was loaded, and not yet
    escalated, becomes one Action to the system administrator. Returns the bundle ids."""
    from apps.core.services import system_admin
    from apps.sync.models.bundle import Bundle
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    stale = (Bundle.objects.filter(purpose=PURPOSE, status='defects',
                                   dt_processed__lte=now_ms - ESCALATE_DAYS * 86_400_000)
             .exclude(config__has_key='escalated_action').order_by('id'))
    if not stale.exists():
        return []
    admin = system_admin.current()
    if admin is None:
        logger.warning('bundle_import: %d bundle(s) unresolved and no system administrator',
                       stale.count())
        return []
    done = []
    for record in stale:
        action = _tell(record, admin)
        record.config = {**(record.config or {}), 'escalated_action': action.pk}
        record.save(update_fields=['config', 'dt_modified', 'version'])
        done.append(record.pk)
    return done


def _tell(record, admin: dict):
    from apps.core.models import Action
    from apps.core.services import select_lists
    name = record.model_name.removeprefix('bundle_')
    defects = (record.response or {}).get('defects') or []
    path = (record.config or {}).get('payload_path')
    if select_lists.unlisted('action', {'purpose': DEFECTS_PURPOSE}):
        select_lists.add_value('action', 'purpose', DEFECTS_PURPOSE, label='Bundle defects')
    shown = '\n'.join(f'- {d}' for d in defects[:SHOWN])
    more = f'\n… and {len(defects) - SHOWN} more on the bundle record.' if len(defects) > SHOWN else ''
    action = Action(
        purpose=DEFECTS_PURPOSE,
        action={'en': f'Resolve {len(defects)} defect(s) in the {name} bundle import (#{record.pk})'},
        description={'en': (
            f'Bundle #{record.pk} ({name}) loaded {ESCALATE_DAYS}+ days ago with {len(defects)} '
            f'record(s) refused, still unresolved. The file '
            f'is in WORK_DIR/{path or "bundles"}; the full list is the bundle record\'s response.'
            f'\n\n{shown}{more}\n\nWhen they are resolved, load it again: '
            f'python manage.py import_bundle --rerun {record.pk}')},
        status='planned',
        priority=3,
        assigned_to=[{'id': admin['id']}],
        refs={'alice': {'source': PURPOSE, 'bundle_id': record.pk}},
    )
    action.save()
    return action
