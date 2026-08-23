"""
Write-Through Proxy — Save to Remote, Store Bundle Locally.

When DB_MODE=write-through, the local database serves all reads while
saves are forwarded to the remote database.  The remote's response
(the "bundle") is stored in the local database so both copies stay
current without a separate sync step.

Flow:
  1. SaveWcapiView receives a POST from the browser.
  2. write_through.forward_save() sends the same payload to remote.
  3. Remote's CoreModel.save() assigns id, uuid, dt_modified, version.
  4. Remote returns the response bundle (standard WCAPI envelope).
  5. write_through.store_bundle() inserts/updates the local DB.
  6. The same response is returned to the browser.

Usage:
  # In save_view.py — called instead of local obj.save() when enabled
  from common.write_through import is_write_through, forward_and_store

  if is_write_through():
      return forward_and_store(request, model_cls)
  else:
      # normal local save path
      ...
"""
import json
import logging
import time
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
    """
    Forward a save payload to the remote database, store the result locally.

    Instead of making an HTTP call to a remote API (which would require
    a running remote Django server and auth forwarding), we save directly
    to the remote database using Django's multi-database ORM — the same
    approach sync_model already uses.

    Args:
        request:   The incoming DRF request (for actor context).
        model_cls: The resolved Django model class.
        payload:   The parsed save payload (model_name, id, field data).

    Returns:
        (response_dict, status_code) to be returned to the browser.
    """
    remote_alias = get_remote_alias()
    record_id = payload.get('id')
    is_update = bool(record_id)
    model_key = payload.get('model_name', model_cls.__name__.lower())

    t0 = time.time()

    try:
        # ── Step 1: Save on remote DB ────────────────────────────────
        if is_update:
            try:
                remote_obj = model_cls.objects.using(remote_alias).get(id=record_id)
            except model_cls.DoesNotExist:
                return {
                    'detail': f'Record {record_id} not found on remote database',
                }, 404
            _apply_fields(remote_obj, payload, model_cls)
            remote_obj.save(using=remote_alias)
            action = 'updated'
            status_code = 200
        else:
            remote_obj = model_cls()
            _apply_fields(remote_obj, payload, model_cls)
            remote_obj.save(using=remote_alias)
            action = 'created'
            status_code = 201

        # ── Step 2: Build the response bundle ────────────────────────
        # Re-read from remote to get the authoritative state
        # (includes anything CoreModel.save() set: id, dt_modified, version, ida)
        remote_obj.refresh_from_db(using=remote_alias)
        bundle = _serialize_record(remote_obj)

        # ── Step 3: Store bundle in local DB ─────────────────────────
        _store_bundle_locally(model_cls, remote_obj, bundle)

        elapsed = time.time() - t0
        logger.info(
            "write-through %s %s id=%s uuid=%s  remote→local  %.1fs",
            action, model_key, remote_obj.pk,
            getattr(remote_obj, 'uuid', None), elapsed,
        )

        # ── Step 4: Return the same shape SaveWcapiView would ────────
        response_payload = {
            'id': remote_obj.pk,
            'record': bundle,
            'model_name': model_key,
            'version': getattr(remote_obj, 'version', None),
            'linked': False,
            'write_through': True,
        }
        return response_payload, status_code

    except Exception as exc:
        elapsed = time.time() - t0
        logger.error(
            "write-through FAILED %s id=%s  %.1fs  %s",
            model_key, record_id, elapsed, exc,
            exc_info=True,
        )
        return {
            'detail': f'Write-through save failed: {str(exc)}',
            'write_through_error': True,
        }, 502


# ── Internal Helpers ────────────────────────────────────────────────


# Fields that should never be forwarded from the save payload
_SKIP_FIELDS = frozenset({
    'model_name', 'id', 'version', 'expected_version',
    'bulk', 'lines', 'password', 'data', 'record', 'options',
})


def _apply_fields(
    obj: models.Model,
    payload: Dict[str, Any],
    model_cls: Type[models.Model],
) -> None:
    """Apply save-payload fields to a model instance.

    Understands the WCAPI field envelope format:
        {"field_name": {"mode": "update", "value": <val>}}
    as well as flat values:
        {"field_name": <val>}
    """
    json_field_names = {
        f.name for f in model_cls._meta.get_fields()
        if hasattr(f, 'attname') and isinstance(f, models.JSONField)
    }

    for field_name, field_data in payload.items():
        if field_name in _SKIP_FIELDS:
            continue

        # Unwrap WCAPI envelope {mode, value}
        if isinstance(field_data, dict) and 'value' in field_data:
            mode = field_data.get('mode', 'update')
            value = field_data['value']
        elif isinstance(field_data, dict) and 'mode' in field_data:
            mode = field_data['mode']
            value = field_data.get('value')
        else:
            mode = 'update'
            value = field_data

        if mode == 'delete':
            if hasattr(obj, field_name):
                setattr(obj, field_name, None)
            continue

        if value is None:
            continue

        if not hasattr(obj, field_name):
            continue

        # JSON field deep-merge
        current = getattr(obj, field_name, None)
        if isinstance(value, dict) and (field_name in json_field_names or isinstance(current, dict)):
            if not isinstance(current, dict):
                current = {}
            from apps.core.views.save_view import deep_merge_dict
            merged = deep_merge_dict(current, value)
            setattr(obj, field_name, merged)
        else:
            setattr(obj, field_name, value)


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


# ── Transaction Write-Through ──────────────────────────────────────


def forward_transaction_and_store(
    request,
    model_key: str,
    record_data: Dict[str, Any],
    lines_data: list,
    options: Dict[str, Any],
) -> Tuple[Dict[str, Any], int]:
    """
    Forward a transaction save (header + lines) to remote, then store
    the saved records in the local database.

    Uses Django's multi-DB ORM: temporarily switches the default DB
    connection for the save_transaction_with_lines service call to the
    remote alias, then copies the resulting records locally.
    """
    remote_alias = get_remote_alias()
    t0 = time.time()

    try:
        from apps.transactions.services.transaction_save import (
            save_transaction_with_lines,
            calculate_header_totals,
        )
        from apps.core.utils import registry

        # ── Step 1: Run the save on the remote database ──────────────
        # We achieve this by temporarily swapping Django's 'default' DB
        # to point at remote. This is the most reliable approach because
        # save_transaction_with_lines uses .objects.create() and .save()
        # without explicit `using=` parameters.
        from django.db import connections as _conns

        # Save original default and swap
        _orig_default = settings.DATABASES.get('default')
        _remote_cfg = settings.DATABASES.get(remote_alias)
        if not _remote_cfg:
            raise RuntimeError(f"Remote DB alias '{remote_alias}' not configured")

        # Use the remote DB alias directly by making save_transaction_with_lines
        # operate through a database router instead of swapping globals.
        # Simpler approach: use Django's `using` on the save service.
        # Since save_transaction_with_lines doesn't accept `using`, we'll
        # apply a thread-local override for the ORM default.

        import threading
        _thread_local = threading.local()

        # Store the original DATABASES['default'] and temporarily swap
        original_default = dict(settings.DATABASES['default'])
        settings.DATABASES['default'] = dict(_remote_cfg)

        # Force Django to reconnect with new settings
        if 'default' in _conns._connections.__dict__:
            _conns['default'].close()
            del _conns._connections.__dict__['default']

        try:
            result = save_transaction_with_lines(
                model_key=model_key.lower(),
                header_data=record_data,
                lines_data=lines_data,
                request=request,
                verify_calculations=options.get("verify_calculations", True),
                save_only_dirty=options.get("save_only_dirty", True),
            )

            recalc_totals = calculate_header_totals(lines_data, record_data)
            result['recalculated_totals'] = {
                k: float(v) for k, v in recalc_totals.items()
            }
        finally:
            # ── Restore the original default DB ──────────────────────
            settings.DATABASES['default'] = original_default
            if 'default' in _conns._connections.__dict__:
                _conns['default'].close()
                del _conns._connections.__dict__['default']

        # ── Step 2: Sync saved records to local DB ───────────────────
        header_id = result.get('header', {}).get('id')
        if header_id:
            HeaderModel = registry.resolve(model_key)
            if HeaderModel:
                try:
                    remote_header = HeaderModel.objects.using(remote_alias).get(pk=header_id)
                    _store_bundle_locally(HeaderModel, remote_header, _serialize_record(remote_header))

                    # Sync lines too
                    LineModel = registry.resolve(f"{model_key}line")
                    if LineModel:
                        remote_lines = LineModel.objects.using(remote_alias).filter(parent_id=header_id)
                        for remote_line in remote_lines:
                            _store_bundle_locally(LineModel, remote_line, _serialize_record(remote_line))
                except Exception as sync_exc:
                    logger.warning(
                        "write-through: remote save OK but local sync failed for %s id=%s: %s",
                        model_key, header_id, sync_exc,
                    )

        elapsed = time.time() - t0
        logger.info(
            "write-through transaction %s id=%s  remote→local  %.1fs",
            model_key, header_id, elapsed,
        )

        result['write_through'] = True
        return result, 200

    except Exception as exc:
        elapsed = time.time() - t0
        logger.error(
            "write-through transaction FAILED %s  %.1fs  %s",
            model_key, elapsed, exc,
            exc_info=True,
        )
        return {
            'detail': f'Write-through transaction save failed: {str(exc)}',
            'write_through_error': True,
        }, 502
