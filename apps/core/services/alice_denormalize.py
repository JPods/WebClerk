"""
Alice's background denormalization service.

Design: ONE permanent Pending record (purpose='alice.denormalize',
name='alice.denormalize.stack') that never closes. The `changes` JSON
field accumulates a stack of {"model": ..., "id": ...} entries.
Each Celery cycle, the processor pops items off the stack, processes
them, and saves the trimmed stack back. No Pending flood.

Replaces WC2's inline RecordToObject balance/keyword calculations.
"""
import logging
from django.db import transaction
from django.db.models import F

logger = logging.getLogger('alice.denormalize')

STACK_NAME = 'alice.denormalize.stack'


def push_to_stack(model_name: str, record_id) -> None:
    """Append a model/id pair to Alice's permanent denormalize stack.

    Called from the post_save signal. Deduplicates — if the same
    model/id is already on the stack, skip it.
    """
    from apps.core.models.pending import Pending

    entry = {'model': model_name, 'id': record_id}

    # Get or create the permanent stack record
    stack, created = Pending.objects.get_or_create(
        purpose='alice.denormalize',
        name=STACK_NAME,
        dt_processed=0,
        defaults={'changes': [entry], 'model_name': 'alice'},
    )

    if created:
        return  # just created with our entry

    # Append if not already on the stack (deduplicate)
    changes = stack.changes if isinstance(stack.changes, list) else []
    if entry not in changes:
        changes.append(entry)
        Pending.objects.filter(pk=stack.pk).update(changes=changes)


def denormalize_record(pending) -> bool:
    """Process Alice's denormalize stack.

    Called by pending_processor. Pops up to BATCH_SIZE items from the
    stack, processes each, then saves the trimmed stack back. The
    Pending record is NEVER marked as processed — it stays open
    permanently.

    Returns True (always — individual item failures don't block the queue).
    """
    BATCH_SIZE = 25

    changes = pending.changes if isinstance(pending.changes, list) else []
    if not changes:
        return True  # nothing to do, but don't close the record

    # Pop a batch from the front of the stack
    batch = changes[:BATCH_SIZE]
    remaining = changes[BATCH_SIZE:]

    processed = 0
    for entry in batch:
        if not isinstance(entry, dict):
            continue
        model_name = entry.get('model', '')
        record_id = entry.get('id')
        if not model_name or record_id is None:
            continue

        try:
            _process_one(model_name, record_id)
            processed += 1
        except Exception:
            logger.exception('alice.denormalize: failed %s:%s', model_name, record_id)
            # Don't put it back — it'll get re-enqueued on next save if still relevant

    # Save the trimmed stack back (never mark processed)
    Pending.objects.filter(pk=pending.pk).update(changes=remaining)

    if processed:
        logger.info('alice.denormalize: processed %d items, %d remaining', processed, len(remaining))

    return True


def _process_one(model_name: str, record_id) -> None:
    """Refresh refs.keywords and propagate refs.links for one record."""
    from apps.core.utils.registry import resolve
    from apps.core.services.link_defaults import MODEL_LINK_TEMPLATES

    ModelCls = resolve(model_name)
    if ModelCls is None:
        return
    if hasattr(ModelCls, 'import_model'):
        ModelCls = ModelCls.import_model()

    # Load the record — skip if locked
    try:
        qs = ModelCls.objects.select_for_update(skip_locked=True).filter(pk=record_id)
        obj = qs.first()
    except Exception:
        obj = ModelCls.objects.filter(pk=record_id).first()

    if obj is None:
        return

    # Refresh keywords
    changed = False
    if hasattr(obj, 'update_keywords'):
        try:
            obj.update_keywords()
            changed = True
        except Exception:
            logger.exception('update_keywords failed for %s:%s', model_name, record_id)

    # Propagate link snapshots to related records
    template = MODEL_LINK_TEMPLATES.get(model_name)
    if template:
        try:
            _propagate_links(obj, model_name, template)
        except Exception:
            logger.exception('link propagation failed for %s:%s', model_name, record_id)

    # Save keywords update (direct update to avoid re-triggering signal)
    if changed:
        update_fields = {}
        if hasattr(obj, 'refs'):
            update_fields['refs'] = obj.refs
        if hasattr(obj, 'metadata'):
            update_fields['metadata'] = obj.metadata
        if update_fields:
            ModelCls.objects.filter(pk=obj.pk).update(**update_fields)


def _propagate_links(obj, model_name: str, template: dict) -> None:
    """Update denormalized link entries on records that reference this object.

    When a customer's name changes, every order/invoice that links to
    that customer gets its refs.links.customer entry updated.
    """
    link_template = template.get('link_template', {})
    if not link_template:
        return

    # Build current snapshot from template
    snapshot = {}
    for key, field_path in link_template.items():
        if field_path is None:
            continue
        val = _resolve_field_path(obj, field_path)
        if val is not None:
            snapshot[key] = val

    if not snapshot or 'id' not in snapshot:
        return

    # Find and update related records
    from django.apps import apps
    from common.models import BaseModel

    for model_cls in apps.get_models():
        if not issubclass(model_cls, BaseModel) or model_cls is BaseModel:
            continue
        if not hasattr(model_cls, 'refs'):
            continue

        lookup = {f'refs__links__{model_name}__contains': [{'id': obj.pk}]}
        try:
            for related in model_cls.objects.filter(**lookup).iterator(chunk_size=100):
                _update_link_entry(related, model_name, obj.pk, snapshot)
        except Exception:
            continue


def _resolve_field_path(obj, path: str):
    """Resolve a dotted field path like 'org.display_name'."""
    current = obj
    for part in str(path).split('.'):
        if hasattr(current, part):
            current = getattr(current, part)
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _update_link_entry(obj, source_model: str, source_id, snapshot: dict) -> None:
    """Update a single link entry in refs.links.<source_model>."""
    refs = getattr(obj, 'refs', None)
    if not isinstance(refs, dict):
        return

    links = refs.get('links')
    if not isinstance(links, dict):
        return

    bucket = links.get(source_model)
    if not isinstance(bucket, list):
        return

    updated = False
    for entry in bucket:
        if not isinstance(entry, dict):
            continue
        entry_id = entry.get('id')
        if entry_id == source_id or str(entry_id) == str(source_id):
            for key, val in snapshot.items():
                if entry.get(key) != val:
                    entry[key] = val
                    updated = True

    if updated:
        try:
            type(obj).objects.filter(pk=obj.pk).update(refs=refs)
        except Exception:
            logger.debug('Failed to propagate link to %s:%s', type(obj).__name__, obj.pk, exc_info=True)
