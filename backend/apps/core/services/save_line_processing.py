"""The lines of a document — the one line engine, run by the save door.

A header saved with ``lines`` (order, invoice, purchase, workorder, quote) has its lines
written here, inside the door's unit of work, after the header is persisted and before
the derived work is flushed. Each line's own door (line_door) writes the Pending for what
the line holds, so the stock and money move with the line, once.

This was two engines until 2026-09-24: this file, and the loop inside
``save_transaction_with_lines`` behind ``/wcapi/transaction/save/``. That loop was the
stricter one, so it is what survives (Bill, 2026-09-24: one door per verb; the route is
deleted, its work moves into the save and the document hooks):

- a line is looked up among **this header's** lines, locked; a line of another document
  is not found, whatever id the payload names;
- a line that is not found is refused, never skipped (Axiom 6);
- an existing line keeps its item — to change the item, delete the line and add one;
- a JSON field on an update merges into what the line holds;
- a new line with no number takes the header's next ``line_increment``;
- a line marked ``_dirty: false`` is left as it is; ``_delete: true`` deletes it;
- ``totals`` are the engine's, never the caller's;
- the header's ``refs.links.<model>_line`` list is the line signal's to keep, once per unit.
"""
from __future__ import annotations

import logging

from django.db import models

from apps.core.constants.model_registry import get_model
from apps.core.services.door import Refused
from common.schemas.carrier import read_carrier

console_logger = logging.getLogger('console')

HEADER_MODELS = frozenset({'order', 'invoice', 'purchase', 'workorder', 'quote'})

LINE_MODEL_MAP = {
    'order': ('OrderLine', 'order'),
    'invoice': ('InvoiceLine', 'invoice'),
    'purchase': ('PurchaseLine', 'purchase'),
    'workorder': ('WorkOrderLine', 'workorder'),
    'quote': ('QuoteLine', 'quote'),
}

#: JSON fields an update merges into, keeping the keys the payload does not name.
MERGE_FIELDS = frozenset({'item', 'quantity', 'cost', 'price', 'tax', 'action', 'physical',
                          'flow', 'source'})


def _normalize_model_key(model_key: str) -> str:
    return model_key.replace('_', '').lower()


def _is_new_line(line_id) -> bool:
    """Detect new lines: null, temp-*, or negative IDs."""
    if line_id is None:
        return True
    if isinstance(line_id, str) and line_id.startswith('temp-'):
        return True
    if isinstance(line_id, (int, float)) and line_id < 0:
        return True
    return False


def _get_fk_descriptors(line_model) -> set:
    """Build set of FK descriptor names to skip during field copy."""
    descriptors = set()
    for f in line_model._meta.get_fields():
        if hasattr(f, 'related_model') and f.related_model is not None:
            descriptors.add(f.name)
    return descriptors


def _copy_line_fields(line_obj, line_data: dict, skip_fields: tuple, fk_descriptors: set,
                      merge: bool):
    """Copy fields from line_data to line_obj, skipping FK descriptors, signals and results."""
    for field_name, field_value in line_data.items():
        if field_name in skip_fields or field_name.startswith('_'):
            continue
        if field_name in fk_descriptors and not isinstance(field_value, models.Model):
            continue
        if not hasattr(line_obj, field_name):
            continue
        if merge and field_name in MERGE_FIELDS and isinstance(field_value, dict):
            held = getattr(line_obj, field_name, None)
            if isinstance(held, dict) and held:
                field_value = {**held, **field_value}
        setattr(line_obj, field_name, field_value)


def _item_id(envelope) -> object:
    if not isinstance(envelope, dict):
        return None
    return envelope.get('item_id') or envelope.get('id')


def _derive_item_fk(line_obj, line_data: dict):
    """Set item_fk_id from item envelope if not already set."""
    if getattr(line_obj, 'item_fk_id', None):
        return
    item_id = _item_id(line_data.get('item'))
    if item_id:
        line_obj.item_fk_id = item_id


def _refuse_item_change(line_obj, line_data: dict, model_key: str) -> None:
    held = _item_id(getattr(line_obj, 'item', None))
    offered = _item_id(line_data.get('item'))
    if held is not None and offered is not None and str(held) != str(offered):
        raise Refused(
            400, 'line_item_change',
            f'Line {line_obj.pk} of this {model_key} is item {held}; its item cannot change. '
            f'Delete the line and add a new one for item {offered}.',
            {'line_id': line_obj.pk, 'held': held, 'offered': offered})


def _line_not_found(line_id, model_key: str, header_id):
    return Refused(404, 'line_not_found',
                   f'Line {line_id} is not a line of {model_key} {header_id}.',
                   {'line_id': line_id, 'model_name': model_key, 'id': header_id})


def process_lines(obj, data: dict, model_key: str) -> list[int]:
    """Write the lines named in ``data['lines']`` for header ``obj`` (already saved).

    Returns the ids of the lines created. Raises ``Refused`` for a line that is not this
    header's, or that tries to change its item; the door rolls the whole save back.
    """
    norm_model = _normalize_model_key(model_key)
    if norm_model not in HEADER_MODELS:
        return []

    lines_data = data.get('lines')
    if not isinstance(lines_data, list):
        return []

    line_model_name, fk_field_name = LINE_MODEL_MAP[norm_model]
    LineModel = get_model(line_model_name.lower())
    if not LineModel:
        raise Refused(500, 'line_model_missing', f'No line model for {model_key}.', model_key)

    fk_descriptors = _get_fk_descriptors(LineModel)
    skip_fields = ('id', 'model_name', 'totals', fk_field_name, f'{fk_field_name}_id',
                   'parent', 'parent_id')
    held = {line.pk: line for line in
            LineModel.objects.select_for_update().filter(**{f'{fk_field_name}_id': obj.pk})}
    first_number = next_number = getattr(obj, 'line_increment', None) or 10
    new_line_ids: list[int] = []
    changed = 0

    for line_data in lines_data:
        if not isinstance(line_data, dict):
            raise Refused(400, 'line_not_an_object', 'Each line is an object.', model_key)
        line_id = line_data.get('id')
        carrier = read_carrier(line_data)      # typed; an unknown signal raises

        if _is_new_line(line_id):
            if carrier.delete:
                continue                       # never saved; nothing to delete
            line_obj = LineModel()
            setattr(line_obj, f'{fk_field_name}_id', obj.pk)
            _copy_line_fields(line_obj, line_data, skip_fields, fk_descriptors, merge=False)
            if not getattr(line_obj, 'line_number', 0):
                line_obj.line_number = next_number
                next_number += 10
            _derive_item_fk(line_obj, line_data)
            line_obj.save()
            new_line_ids.append(line_obj.pk)
            changed += 1
            continue

        line_obj = held.get(_as_pk(line_id))
        if line_obj is None:
            raise _line_not_found(line_id, model_key, obj.pk)

        # A removed line arrives marked (Bill, 2026-09-22); the backend deletes it, and the
        # line's post_delete writes the Pending that releases what it held.
        if carrier.delete:
            line_obj.delete()
            changed += 1
            continue
        if not carrier.dirty:
            continue

        _refuse_item_change(line_obj, line_data, model_key)
        _copy_line_fields(line_obj, line_data, skip_fields, fk_descriptors, merge=True)
        _derive_item_fk(line_obj, line_data)
        line_obj.save()
        changed += 1

    if next_number != first_number and hasattr(obj, 'line_increment'):
        obj.line_increment = next_number
        obj.save(update_fields=['line_increment', 'version', 'dt_modified'])
    if changed:
        from apps.products.dispatch_pending import dispatch_pending_processing
        dispatch_pending_processing(limit=200, caller='save_line_processing')
    return new_line_ids


def _as_pk(line_id):
    try:
        return int(line_id)
    except (TypeError, ValueError):
        return line_id
