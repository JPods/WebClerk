"""
Async Remote Sync — Celery tasks for local-sync DB mode.

When DB_MODE=local-sync, saves happen locally (fast) and a Celery task
pushes the record + its entire FK dependency tree to the remote database
in a single bundled send.

Bundle strategy (§25.1 relationship preservation):
    Instead of cascade-syncing each FK dependency one at a time (many
    slow round trips), we:
      1. COLLECT — walk the record's FK tree locally (fast) to build a
         dependency graph of all related records
      2. ORDER — topological sort so leaf records (orgs) come before
         dependents (contacts) before the main record
      3. PUSH — iterate the sorted bundle, push each to remote, building
         a uuid→remote_pk map as we go
      4. RESOLVE — FK values on later records in the bundle use the map
         rather than individual remote queries

    Example bundle for an Order save:
      [OrgBase#87, OrgBase#69, Contact#40, Order#12, OrderLine#15, OrderLine#16]

    This turns N separate remote round trips into one ordered batch.

See §25 Sync Topologies in data-sync-consolidated.md.
"""
from __future__ import annotations

import logging
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Set, Tuple

from celery import shared_task
from django.conf import settings
from django.db import connections, models
from django.utils import timezone

logger = logging.getLogger('wcapi.sync_tasks')

# Transaction header model keys that have child line models
HEADER_MODEL_KEYS = frozenset({
    'order', 'invoice', 'purchase', 'workorder', 'proposal', 'requisition',
})

# Max depth for FK dependency collection (prevents cycles)
MAX_FK_DEPTH = 3


# ── Configuration ────────────────────────────────────────────────────

def is_local_sync() -> bool:
    """Return True when local-sync mode is active."""
    return getattr(settings, 'LOCAL_SYNC_ENABLED', False)


def get_remote_alias() -> str:
    """Return the Django DB alias for the remote database."""
    return getattr(settings, 'WRITE_THROUGH_REMOTE_ALIAS', '_wt_remote')


# ── Celery Task ──────────────────────────────────────────────────────

@shared_task(
    bind=True,
    name='common.sync_tasks.sync_record_to_remote',
    autoretry_for=(Exception,),
    retry_backoff=True,          # exponential: 1s, 2s, 4s, 8s, …
    retry_backoff_max=300,       # cap at 5 minutes
    max_retries=10,
    retry_jitter=True,
    acks_late=True,
    reject_on_worker_lost=True,
)
def sync_record_to_remote(
    self,
    model_key: str,
    record_id: int,
) -> Dict[str, Any]:
    """Push a locally saved record + FK deps to the remote DB in one bundle.

    Works for ANY model — contacts, orgs, communications, transactions.
    For transaction headers, child lines are included in the bundle.

    Steps:
      1. Collect FK dependency tree locally (fast, no remote hits)
      2. Add child lines for transaction headers
      3. Push entire bundle to remote in dependency order
      4. Mark the primary record as synced

    Args:
        model_key:  WCAPI model key (e.g. "order", "contact", "orgbase")
        record_id:  PK of the record on the local database

    Returns:
        dict with sync result info.
    """
    from apps.core.utils import registry
    from apps.products.dispatch_pending import mark_worker_alive

    mark_worker_alive()

    remote_alias = get_remote_alias()
    t0 = time.time()

    # ── Resolve model ─────────────────────────────────────────────
    Model = registry.resolve(model_key)
    if Model is None:
        msg = f"sync_record_to_remote: unknown model_key '{model_key}'"
        logger.error(msg)
        return {'ok': False, 'error': msg}

    # ── Read local record ─────────────────────────────────────────
    try:
        local_obj = Model.objects.using('default').get(pk=record_id)
    except Model.DoesNotExist:
        msg = f"sync_record_to_remote: {model_key} id={record_id} not found locally"
        logger.error(msg)
        return {'ok': False, 'error': msg}

    # ── Phase 1: Collect dependency bundle (local reads only) ─────
    bundle: OrderedDict[str, Tuple[type, models.Model]] = OrderedDict()
    _collect_fk_deps(Model, local_obj, bundle, depth=0)

    # ── Phase 2: Add child lines for transaction headers ──────────
    lines_synced = 0
    norm_key = model_key.lower().replace('_', '')
    if norm_key in HEADER_MODEL_KEYS:
        line_model_key = f"{norm_key}line"
        LineModel = registry.resolve(line_model_key)
        if LineModel is not None:
            parent_fk = _find_parent_fk(LineModel, Model, norm_key)
            if parent_fk:
                local_lines = LineModel.objects.using('default').filter(
                    **{parent_fk: record_id}
                ).order_by('id')
                for local_line in local_lines:
                    line_key = f"{LineModel.__name__}:{local_line.pk}"
                    if line_key not in bundle:
                        # Collect line's own FK deps too (e.g. item_fk)
                        _collect_fk_deps(LineModel, local_line, bundle, depth=1)

    # ── Phase 3: Push bundle to remote in dependency order ────────
    #   bundle is ordered: leaf deps first → main record → lines last
    #   uuid_map tracks local_uuid → remote_pk for FK resolution
    uuid_map: Dict[str, int] = {}  # uuid_str → remote pk
    records_pushed = 0

    try:
        for bundle_key, (model_cls, local) in bundle.items():
            _push_one_to_remote(model_cls, local, remote_alias, uuid_map)
            records_pushed += 1
            # Count lines
            if 'Line:' in bundle_key or 'line:' in bundle_key.lower():
                lines_synced += 1
    except Exception as exc:
        logger.warning(
            "sync_record_to_remote: bundle push failed at record %d/%d "
            "(attempt %s/%s): %s",
            records_pushed, len(bundle),
            self.request.retries + 1, self.max_retries, exc,
        )
        raise  # triggers Celery auto-retry

    # ── Phase 4: Mark primary record as synced ────────────────────
    _mark_synced(Model, record_id)

    elapsed = time.time() - t0
    logger.info(
        "sync_record_to_remote OK  %s id=%s  bundle=%d  lines=%d  %.1fs",
        model_key, record_id, len(bundle), lines_synced, elapsed,
    )
    return {
        'ok': True,
        'model_key': model_key,
        'record_id': record_id,
        'bundle_size': len(bundle),
        'lines_synced': lines_synced,
        'elapsed': round(elapsed, 2),
    }


# Legacy alias — existing wiring in transaction views uses this name
sync_transaction_to_remote = sync_record_to_remote


# ── Phase 1: Dependency Collection (local reads only) ────────────────

def _collect_fk_deps(
    model_cls: type[models.Model],
    local_obj: models.Model,
    bundle: OrderedDict,
    depth: int = 0,
) -> None:
    """Walk FK fields and collect dependency records into the bundle.

    Adds records in dependency-first order: an org referenced by a contact
    is added BEFORE the contact so it exists on remote when the contact
    is pushed.  The main record is added last.

    All reads are against the local DB (fast).
    """
    record_key = f"{model_cls.__name__}:{local_obj.pk}"
    if record_key in bundle:
        return  # already collected (avoids cycles)
    if depth > MAX_FK_DEPTH:
        # Still add the record itself, just don't recurse deeper
        bundle[record_key] = (model_cls, local_obj)
        return

    # Recurse into FK dependencies first (so they appear earlier in bundle)
    for field in model_cls._meta.concrete_fields:
        if not isinstance(field, models.ForeignKey):
            continue
        fk_val = getattr(local_obj, field.attname)
        if fk_val is None:
            continue
        related_model = field.related_model
        try:
            related_obj = related_model.objects.using('default').get(pk=fk_val)
            _collect_fk_deps(related_model, related_obj, bundle, depth + 1)
        except related_model.DoesNotExist:
            logger.debug(
                "FK dep not found locally: %s.%s → %s pk=%s",
                model_cls.__name__, field.name,
                related_model.__name__, fk_val,
            )

    # Add THIS record after its deps
    bundle[record_key] = (model_cls, local_obj)


# ── Phase 3: Push one record to remote ───────────────────────────────

def _push_one_to_remote(
    model_cls: type[models.Model],
    local_obj: models.Model,
    remote_alias: str,
    uuid_map: Dict[str, int],
) -> None:
    """Insert or update a single record on the remote database.

    Uses uuid_map (populated by earlier bundle entries) to resolve FK
    values without additional remote queries.  Falls back to uuid lookup
    on remote when the map doesn't have the answer.

    uuid is never overwritten on remote.
    """
    uuid_val = getattr(local_obj, 'uuid', None)
    remote_obj = None

    # Try uuid match first, then PK
    if uuid_val:
        remote_obj = model_cls.objects.using(remote_alias).filter(uuid=uuid_val).first()
    if remote_obj is None:
        remote_obj = model_cls.objects.using(remote_alias).filter(pk=local_obj.pk).first()

    # Identify FK fields
    fk_fields = {
        f.attname: f
        for f in model_cls._meta.concrete_fields
        if isinstance(f, models.ForeignKey)
    }

    if remote_obj is not None:
        # ── Update existing remote record ─────────────────────────
        changed = False
        for field in model_cls._meta.concrete_fields:
            if field.attname == 'uuid':
                continue  # immutable
            attr = field.attname

            if attr in fk_fields:
                resolved = _resolve_fk_via_map(
                    fk_fields[attr], local_obj, remote_alias, uuid_map,
                )
                if resolved != getattr(remote_obj, attr, None):
                    setattr(remote_obj, attr, resolved)
                    changed = True
            else:
                local_val = getattr(local_obj, attr, None)
                remote_val = getattr(remote_obj, attr, None)
                if local_val != remote_val:
                    setattr(remote_obj, attr, local_val)
                    changed = True

        if changed:
            remote_obj._sync_in_progress = True
            models.Model.save(remote_obj, using=remote_alias)
    else:
        # ── Create new remote record ──────────────────────────────
        remote_obj = model_cls()
        for field in model_cls._meta.concrete_fields:
            attr = field.attname
            if attr in fk_fields:
                resolved = _resolve_fk_via_map(
                    fk_fields[attr], local_obj, remote_alias, uuid_map,
                )
                setattr(remote_obj, attr, resolved)
            else:
                setattr(remote_obj, attr, getattr(local_obj, attr, None))
        remote_obj._sync_in_progress = True
        models.Model.save(remote_obj, using=remote_alias)

    # Register in uuid_map so later bundle entries can resolve to this
    if uuid_val:
        uuid_map[str(uuid_val)] = remote_obj.pk

    # Reset sequence on remote
    _reset_remote_sequence(model_cls, remote_alias)


# ── FK Resolution via bundle map ─────────────────────────────────────

def _resolve_fk_via_map(
    field: models.ForeignKey,
    local_obj: models.Model,
    remote_alias: str,
    uuid_map: Dict[str, int],
) -> int | None:
    """Translate a local FK value to the correct remote PK.

    Resolution order (fastest first):
      1. uuid_map — populated by earlier records in the same bundle (free)
      2. Remote uuid lookup — single query if not in map
      3. Raw value fallback — when related record has no uuid

    No cascade sync needed — deps are already in the bundle.
    """
    local_fk_val = getattr(local_obj, field.attname)
    if local_fk_val is None:
        return None

    related_model = field.related_model

    # Step 1: Look up related local object for its uuid
    try:
        local_related = related_model.objects.using('default').get(pk=local_fk_val)
    except related_model.DoesNotExist:
        return local_fk_val  # can't resolve, use raw

    uuid_val = getattr(local_related, 'uuid', None)
    if not uuid_val:
        return local_fk_val  # no uuid → same PK space

    uuid_str = str(uuid_val)

    # Step 2: Check bundle map (already pushed)
    if uuid_str in uuid_map:
        return uuid_map[uuid_str]

    # Step 3: Query remote (dep might have been synced in a prior task)
    remote_related = (
        related_model.objects.using(remote_alias)
        .filter(uuid=uuid_val)
        .only('pk')
        .first()
    )
    if remote_related:
        uuid_map[uuid_str] = remote_related.pk  # cache for later
        return remote_related.pk

    logger.warning(
        "FK resolve MISS: %s.%s → %s uuid=%s not on remote, using local pk=%s",
        type(local_obj).__name__, field.name,
        related_model.__name__, uuid_str, local_fk_val,
    )
    return local_fk_val  # final fallback


# ── Utility Helpers ──────────────────────────────────────────────────

def _reset_remote_sequence(model_cls: type[models.Model], alias: str) -> None:
    """Reset PostgreSQL auto-increment to MAX(id)+1 on the given database."""
    table = model_cls._meta.db_table
    pk_col = model_cls._meta.pk.column
    sql = (
        f"SELECT setval(pg_get_serial_sequence('{table}', '{pk_col}'), "
        f"COALESCE(MAX({pk_col}), 0) + 1, false) FROM \"{table}\""
    )
    try:
        with connections[alias].cursor() as cursor:
            cursor.execute(sql)
    except Exception as exc:
        logger.debug("Sequence reset skipped for %s on %s: %s", table, alias, exc)


def _mark_synced(model_cls: type[models.Model], record_id: int) -> None:
    """Update metadata.history.synced.dt on the local record."""
    now_ms = int(timezone.now().timestamp() * 1000)
    try:
        obj = model_cls.objects.using('default').get(pk=record_id)
        if hasattr(obj, 'metadata') and isinstance(obj.metadata, dict):
            history = obj.metadata.setdefault('history', {})
            history['synced'] = {'dt': now_ms, 'contact_id': 0}
            model_cls.objects.using('default').filter(pk=record_id).update(
                metadata=obj.metadata,
            )
    except Exception as exc:
        logger.warning("Failed to mark %s id=%s as synced: %s",
                        model_cls.__name__, record_id, exc)


def _find_parent_fk(
    line_model: type[models.Model],
    header_model: type[models.Model],
    model_key: str,
) -> Optional[str]:
    """Find the FK field name on the line model that points to the header."""
    try:
        from apps.transactions.services.transaction_save import _resolve_parent_fk
        return _resolve_parent_fk(line_model, header_model, model_key)
    except Exception:
        pass
    for field in line_model._meta.fields:
        if isinstance(field, models.ForeignKey):
            if field.related_model is header_model:
                return field.name
    return 'parent_id'


# ── Dispatch helper (used by views) ──────────────────────────────────

def dispatch_sync_to_remote(model_key: str, record_id: int) -> Optional[str]:
    """Queue a sync task if local-sync mode is active.

    Works for any model — contacts, orgs, communications, transactions.
    Returns the Celery task ID if dispatched, None otherwise.
    """
    if not is_local_sync():
        return None

    try:
        result = sync_record_to_remote.apply_async(
            kwargs={
                'model_key': model_key,
                'record_id': record_id,
            },
            countdown=3,  # small delay to let the DB transaction commit
        )
        logger.info(
            "Dispatched sync_record_to_remote  %s id=%s  task_id=%s",
            model_key, record_id, result.id,
        )
        return result.id
    except Exception as exc:
        logger.warning(
            "Failed to dispatch sync task for %s id=%s: %s  (will retry via beat)",
            model_key, record_id, exc,
        )
        return None
