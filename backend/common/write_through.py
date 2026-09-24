"""
Write-Through Proxy — Save to Remote, Store Bundle Locally.

When DB_MODE=write-through, the local database serves all reads while
saves are forwarded to the remote database.  The remote's response
(the "bundle") is stored in the local database so both copies stay
current without a separate sync step.

Flow (one door, Bill 2026-09-22 and 2026-09-24):
  1. The REST save (SaveWcapiView) sees write-through mode.
  2. forward_and_store() runs the save door — save_record, with the caller's actor, its
     authorization, hooks and lines — against the remote database.
  3. The saved record, and a document's lines, are copied into the local database.
  4. The browser gets the same response shape as a local save.
"""
import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional, Tuple, Type

from django.conf import settings
from django.db import connections, models
from django.forms.models import model_to_dict

logger = logging.getLogger('wcapi.write_through')


# ── Public API ──────────────────────────────────────────────────────


def is_write_through() -> bool:
    """Return True when write-through mode is active."""
    return getattr(settings, 'WRITE_THROUGH_ENABLED', False)


def get_remote_alias() -> str:
    """Return the Django DB alias for the remote database."""
    return getattr(settings, 'WRITE_THROUGH_REMOTE_ALIAS', '_wt_remote')


def forward_and_store(
    request,
    model_cls: Type[models.Model],
    payload: Dict[str, Any],
) -> Tuple[Dict[str, Any], int]:
    """Save through the door on the remote database, then mirror the result locally.

    The remote is authoritative, so the save — authorization, hooks, lines, the Pendings
    the lines write — happens there, through ``save_record`` like every other save. There
    is no second writer: until 2026-09-24 this applied payload fields straight onto a
    remote row, outside the door, and a document's lines went through a separate route.

    Returns ``(response_dict, status_code)``: the door's refusal keeps its own status; a
    remote that cannot be reached is 502.
    """
    from apps.core.services.door import Actor, Refused
    from apps.core.services.save import save_record
    from apps.core.views.save_view import coerce_int

    remote_alias = get_remote_alias()
    model_key = payload.get('model_name', model_cls.__name__.lower())
    actor = Actor.from_request(request)
    t0 = time.time()

    try:
        with _remote_as_default(remote_alias):
            result = save_record(actor, payload, record_id=coerce_int(payload.get('id')),
                                 expected_version=coerce_int(payload.get('version')))
        remote_obj = model_cls.objects.using(remote_alias).get(pk=result.obj_id)
        bundle = _serialize_record(remote_obj)
        _store_bundle_locally(model_cls, remote_obj, bundle)
        _store_lines_locally(result.model_key, remote_obj, remote_alias)
    except Refused as refused:
        return {'detail': refused.message, 'code': refused.code,
                'details': refused.details}, refused.status
    except Exception as exc:  # noqa: BLE001 — the remote is unreachable or failed
        logger.error("write-through FAILED %s id=%s  %.1fs  %s", model_key,
                     payload.get('id'), time.time() - t0, exc, exc_info=True)
        return {
            'detail': f'Write-through save failed: {str(exc)}',
            'write_through_error': True,
        }, 502

    logger.info("write-through %s %s id=%s  remote→local  %.1fs",
                'created' if result.created else 'updated', model_key, remote_obj.pk,
                time.time() - t0)
    return {
        'id': remote_obj.pk,
        'record': bundle,
        'model_name': result.model_key,
        'version': getattr(remote_obj, 'version', None),
        'linked': result.linked,
        'messages': result.messages,
        'write_through': True,
    }, 201 if result.created else 200


@contextmanager
def _remote_as_default(remote_alias: str):
    """Point the ORM's default connection at the remote for the length of one save.

    The door writes through ``Model.objects`` without ``using=``, so the save runs against
    whatever 'default' is. This swaps the connection settings and reconnects; it is
    process-wide, so write-through is for a single-worker desktop, not a threaded server.
    """
    if remote_alias == 'default':
        yield
        return
    remote_cfg = settings.DATABASES.get(remote_alias)
    if not remote_cfg:
        raise RuntimeError(f"Remote DB alias '{remote_alias}' not configured")
    original = dict(settings.DATABASES['default'])

    def _reconnect():
        if 'default' in connections._connections.__dict__:
            connections['default'].close()
            del connections._connections.__dict__['default']

    settings.DATABASES['default'] = dict(remote_cfg)
    _reconnect()
    try:
        yield
    finally:
        settings.DATABASES['default'] = original
        _reconnect()


def _store_lines_locally(model_key: str, remote_header, remote_alias: str) -> None:
    """A document's lines follow their header into the local database."""
    from apps.core.constants.model_registry import get_model
    from apps.core.services.save_line_processing import LINE_MODEL_MAP
    mapped = LINE_MODEL_MAP.get(model_key)
    if not mapped:
        return
    LineModel = get_model(mapped[0].lower())
    by_header = {f'{mapped[1]}_id': remote_header.pk}
    remote_lines = list(LineModel.objects.using(remote_alias).filter(**by_header))
    for remote_line in remote_lines:
        _store_bundle_locally(LineModel, remote_line, _serialize_record(remote_line))
    # A line the remote deleted is gone here too. A raw delete, which sends no signals: the
    # remote already wrote the Pendings; this copy mirrors, it does not act.
    gone = LineModel.objects.using('default').filter(**by_header).exclude(
        uuid__in=[line.uuid for line in remote_lines])
    gone._raw_delete(gone.db)


# ── Internal Helpers ────────────────────────────────────────────────


def _serialize_record(obj: models.Model) -> Dict[str, Any]:
    """Serialize a model instance to a dict suitable for the response bundle."""
    try:
        safe_fields = [f.name for f in obj._meta.concrete_fields]
        record = model_to_dict(obj, fields=safe_fields)
        # model_to_dict skips non-editable fields; add them manually
        for f in obj._meta.concrete_fields:
            if not f.editable and f.name not in record:
                record[f.name] = getattr(obj, f.name, None)
        # Ensure uuid is serialized as string
        uuid_val = record.get('uuid')
        if uuid_val is not None:
            record['uuid'] = str(uuid_val)
        return record
    except Exception:
        return {'id': getattr(obj, 'id', None)}


def _store_bundle_locally(
    model_cls: Type[models.Model],
    remote_obj: models.Model,
    bundle: Dict[str, Any],
) -> None:
    """Insert or update the local DB from the remote's saved record.

    Uses the uuid as the cross-database identity (authoritative match).
    Falls back to PK if uuid is not available.
    """
    uuid_val = getattr(remote_obj, 'uuid', None)
    local_obj = None

    # Try to find existing local record by uuid first, then by PK
    if uuid_val:
        local_obj = model_cls.objects.using('default').filter(uuid=uuid_val).first()
    if local_obj is None:
        local_obj = model_cls.objects.using('default').filter(pk=remote_obj.pk).first()

    if local_obj is not None:
        # Update existing local record with remote's authoritative values.
        # In write-through, remote is the primary — its ida is authoritative.
        # Only uuid is truly immutable across databases (see §25 Sync Topologies).
        for field in model_cls._meta.concrete_fields:
            if field.name == 'uuid':
                continue  # never overwrite uuid (immutable cross-DB key)
            remote_val = getattr(remote_obj, field.name, None)
            setattr(local_obj, field.name, remote_val)
        # Bypass CoreModel.save() version/timestamp logic — store remote's exact values
        local_obj._sync_in_progress = True
        models.Model.save(local_obj, using='default')
    else:
        # Create new local record mirroring remote exactly
        local_obj = model_cls()
        for field in model_cls._meta.concrete_fields:
            setattr(local_obj, field.name, getattr(remote_obj, field.name, None))
        local_obj._sync_in_progress = True
        models.Model.save(local_obj, using='default')

    # Reset PK sequence to avoid collisions on future local inserts
    _reset_local_sequence(model_cls)


def _reset_local_sequence(model_cls: Type[models.Model]) -> None:
    """Reset PostgreSQL auto-increment to MAX(id)+1 on the local database."""
    table = model_cls._meta.db_table
    pk_col = model_cls._meta.pk.column
    sql = (
        f"SELECT setval(pg_get_serial_sequence('{table}', '{pk_col}'), "
        f"COALESCE(MAX({pk_col}), 0) + 1, false) FROM \"{table}\""
    )
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute(sql)
    except Exception as exc:
        # Non-fatal — sequence may not exist for UUID PKs
        logger.debug("Sequence reset skipped for %s: %s", table, exc)
