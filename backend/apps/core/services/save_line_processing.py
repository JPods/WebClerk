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
- only the line's own fields are written; any other key (``pk``) is refused, never dropped
  (A3-H-1: ``{"id": 5, "pk": 9999}`` wrote line 5's data over line 9999 of any document);
- a line's identity never changes: its document, and its item's id, ida and uuid (Bill,
  2026-10-07) — to change the item, delete the line and add one;
- a line sent with its ``version`` is refused 412 when another save changed it first;
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

# A receipt's lines were dropped without a word until 2026-09-27 (found building purchase.receive,
# R3). Lines sent to any other model are refused, never dropped. Requisition is one: on hold until
# 2026-11-27 (Bill, 2026-09-27; action 31281), its lines are refused until the review.
HEADER_MODELS = frozenset({'order', 'invoice', 'purchase', 'workorder', 'quote', 'receipt'})

LINE_MODEL_MAP = {
    'order': ('OrderLine', 'order'),
    'invoice': ('InvoiceLine', 'invoice'),
    'purchase': ('PurchaseLine', 'purchase'),
    'workorder': ('WorkOrderLine', 'workorder'),
    'quote': ('QuoteLine', 'quote'),
    'receipt': ('ReceiptLine', 'receipt'),
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


#: What names a line's item. None of it changes once the line is saved (Bill, 2026-10-07).
ITEM_IDENTITY_KEYS = ('ida_item', 'uuid_item')


def _writable_fields(line_model, skip_fields: tuple) -> dict:
    """The keys a line payload may name → the attribute each one writes.

    A line's concrete fields, by name and by column (``item_fk`` and ``item_fk_id`` both
    write ``item_fk_id``). Nothing else: ``pk``, a property or a reverse relation is no field
    of the line, and is refused rather than set (A3-H-1).
    """
    writable = {}
    for f in line_model._meta.concrete_fields:
        for key in (f.name, f.attname):
            if key not in skip_fields:
                writable[key] = f.attname
    return writable


def _stamp_line_comments(line_data: dict, actor) -> None:
    """A comment entry sent with a line (an adjust line's reason) is stamped by the server with
    who and when, as CommentsPanel's are; an entry that already carries its time is left alone."""
    from apps.core.services.comment_stamp import stamp
    comments = line_data.get('comments')
    if not isinstance(comments, dict):
        return
    user = getattr(actor, 'user', None) if actor is not None else None
    for entries in comments.values():
        for entry in entries if isinstance(entries, list) else []:
            if isinstance(entry, dict) and not entry.get('time'):
                entry.update({k: v for k, v in stamp(user).items() if not entry.get(k)})


def _copy_line_fields(line_obj, line_data: dict, skip_fields: tuple, writable: dict,
                      merge: bool, model_key: str):
    """Copy the line's own fields from line_data; refuse any key that is not one."""
    from apps.core.services.save_field_assignment import _coach_unknown
    from apps.core.services.dt_fields import SYSTEM_DT_FIELDS
    from apps.core.services.save import _same_as_stored

    unknown = [key for key in line_data
               if key not in skip_fields and key != 'version' and not key.startswith('_')
               and key not in writable]
    if unknown:
        json_names = {f.name for f in type(line_obj)._meta.concrete_fields
                      if isinstance(f, models.JSONField)}
        details = [_coach_unknown(key, type(line_obj), json_names) for key in unknown]
        raise Refused(400, 'unknown_field', f"Not fields of a {model_key} line: " + '; '.join(details),
                      {'line_id': line_data.get('id'), 'unknown': details})
    for field_name, field_value in line_data.items():
        if field_name in skip_fields or field_name == 'version' or field_name.startswith('_'):
            continue
        attname = writable[field_name]
        if attname in SYSTEM_DT_FIELDS or (attname == 'ida' and line_obj.pk):
            # Written by its event, as on the header (Bill, 2026-09-28): an echo is left alone.
            if not _same_as_stored(line_obj, attname, field_value):
                raise Refused(400, 'system_field' if attname != 'ida' else 'ida_locked',
                              f"A line's {attname} is the server's; it cannot be sent.",
                              {'line_id': line_obj.pk, 'field': attname})
            continue
        if merge and attname in MERGE_FIELDS and isinstance(field_value, dict):
            held = getattr(line_obj, attname, None)
            if isinstance(held, dict) and held:
                field_value = {**held, **field_value}
        setattr(line_obj, attname, field_value)


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


def _same(a, b) -> bool:
    return (a in (None, '') and b in (None, '')) or str(a) == str(b)


def _item_identity(line_obj) -> dict:
    envelope = getattr(line_obj, 'item', None) or {}
    envelope = envelope if isinstance(envelope, dict) else {}
    return {'item_fk_id': getattr(line_obj, 'item_fk_id', None), 'item_id': _item_id(envelope),
            **{k: envelope.get(k) for k in ITEM_IDENTITY_KEYS}}


def _refuse_identity_change(line_obj, held: dict, model_key: str) -> None:
    """A saved line's item is its identity: id, ida and uuid never change (Bill, 2026-10-07).
    To change the item, delete the line and add one."""
    now = _item_identity(line_obj)
    changed = sorted(k for k in now if not _same(held[k], now[k])
                     # the column filled from the envelope it already held is not a change
                     and not (k == 'item_fk_id' and held[k] in (None, '')
                              and _same(now[k], held['item_id'])))
    if changed:
        raise Refused(
            400, 'line_item_change',
            f"Line {line_obj.pk} of this {model_key} is item {held['item_id'] or held['item_fk_id']}; "
            f"its item cannot change ({', '.join(changed)}). Delete the line and add a new one.",
            {'line_id': line_obj.pk, 'changed': changed,
             'held': {k: held[k] for k in changed}, 'offered': {k: now[k] for k in changed}})


def _settle_new_line_item(line_obj, model_key: str) -> None:
    """A new line's item is named once, and named the same everywhere: the column, the
    envelope's id, and the ida and uuid of that Item. A blank ida or uuid is filled from the
    Item; one that names another item is refused."""
    ident = _item_identity(line_obj)
    if ident['item_fk_id'] and ident['item_id'] and not _same(ident['item_fk_id'], ident['item_id']):
        raise Refused(400, 'line_item_mismatch',
                      f"item_fk {ident['item_fk_id']} and item.item_id {ident['item_id']} name two items.",
                      {'item_fk_id': ident['item_fk_id'], 'item_id': ident['item_id']})
    item_pk = ident['item_fk_id'] or ident['item_id']
    if not item_pk:
        return                                  # a line with no item (shipping, a note)
    from apps.products.models import Item
    item = Item.objects.filter(pk=_as_pk(item_pk)).only('pk', 'ida', 'uuid').first()
    if item is None:
        raise Refused(400, 'line_item_not_found', f'Item {item_pk} does not exist.', {'item_id': item_pk})
    truth = {'ida_item': item.ida or '', 'uuid_item': str(item.uuid) if item.uuid else ''}
    wrong = sorted(k for k in ITEM_IDENTITY_KEYS if ident[k] not in (None, '') and not _same(ident[k], truth[k]))
    if wrong:
        raise Refused(400, 'line_item_mismatch',
                      f"Item {item.pk} is {truth['ida_item']}; the line names another ({', '.join(wrong)}).",
                      {'item_id': item.pk, 'offered': {k: ident[k] for k in wrong},
                       'item': {k: truth[k] for k in wrong}})
    envelope = dict(getattr(line_obj, 'item', None) or {})
    envelope.update({'item_id': item.pk, **truth})
    line_obj.item = envelope
    line_obj.item_fk_id = item.pk


def _line_not_found(line_id, model_key: str, header_id):
    return Refused(404, 'line_not_found',
                   f'Line {line_id} is not a line of {model_key} {header_id}.',
                   {'line_id': line_id, 'model_name': model_key, 'id': header_id})


def process_lines(obj, data: dict, model_key: str, actor=None) -> list[int]:
    """Write the lines named in ``data['lines']`` for header ``obj`` (already saved).

    ``actor`` is who is saving: each line carries it (``line._actor``) to its door, which
    records it on the line's event and refuses a count nobody is responsible for (plan §16c).

    Returns the ids of the lines created. Raises ``Refused`` for a line that is not this
    header's, or that tries to change its item; the door rolls the whole save back.
    """
    norm_model = _normalize_model_key(model_key)
    lines_data = data.get('lines')
    if lines_data is None or lines_data == []:
        return []
    if norm_model not in HEADER_MODELS:
        raise Refused(400, 'lines_not_accepted', f'{model_key} records have no lines; nothing was saved.',
                      model_key)
    if not isinstance(lines_data, list):
        raise Refused(400, 'lines_not_a_list', '"lines" must be a list of lines.', model_key)

    line_model_name, fk_field_name = LINE_MODEL_MAP[norm_model]
    LineModel = get_model(line_model_name.lower())
    if not LineModel:
        raise Refused(500, 'line_model_missing', f'No line model for {model_key}.', model_key)

    # uuid is set once, on a new line, and never copied onto an existing one (a line's uuid
    # cannot change: common/models.py raises — it was an uncaught 500).
    skip_fields = ('id', 'uuid', 'model_name', 'totals', fk_field_name, f'{fk_field_name}_id',
                   'parent', 'parent_id')
    writable = _writable_fields(LineModel, skip_fields)
    held = {line.pk: line for line in
            LineModel.objects.select_for_update().filter(**{f'{fk_field_name}_id': obj.pk})}
    by_uuid = {str(line.uuid): line.pk for line in held.values() if getattr(line, 'uuid', None)}
    first_number = next_number = getattr(obj, 'line_increment', None) or 10
    new_line_ids: list[int] = []
    changed = 0

    for line_data in lines_data:
        if not isinstance(line_data, dict):
            raise Refused(400, 'line_not_an_object', 'Each line is an object.', model_key)
        line_id = line_data.get('id')
        keep_uuid = None
        if _is_new_line(line_id) and line_data.get('uuid'):
            # A line named by uuid (plan §17.13): this document's line with that uuid, or a new
            # line that keeps it.
            import uuid as _uuid
            try:
                keep_uuid = _uuid.UUID(str(line_data['uuid']))
            except (ValueError, AttributeError, TypeError):
                raise Refused(400, 'bad_uuid', f'"{line_data["uuid"]}" is not a uuid.', model_key)
            line_id = by_uuid.get(str(keep_uuid)) or line_id
            if not _is_new_line(line_id):
                keep_uuid = None
            elif LineModel.objects.filter(uuid=keep_uuid).exists():
                raise Refused(409, 'line_uuid_elsewhere',
                              f'Line uuid {keep_uuid} belongs to another document.', model_key)
        carrier = read_carrier(line_data)      # typed; an unknown signal raises
        refs = line_data.get('refs') if isinstance(line_data.get('refs'), dict) else {}
        if 'bom' in refs or 'bom_expand' in refs:
            # Expand writes where a line came from; a request never re-links it (Fable #10).
            raise Refused(400, 'bom_link_is_the_record',
                          "A line's BOM link is set by expand; expand again to change it.",
                          {'line_id': line_data.get('id')})
        if 'events' in line_data:
            # A line's events are what the applier did to it; a request never writes them.
            raise Refused(400, 'events_are_the_record',
                          "A line's events are written by the server as stock moves; send the change, "
                          "not the record of it.", {'line_id': line_data.get('id')})
        for key in (fk_field_name, f'{fk_field_name}_id', 'parent', 'parent_id'):
            if key in line_data and not _same(line_data[key], obj.pk):
                # The document a line belongs to is its identity: an echo of it is fine,
                # another document is a move, and a line never moves (Bill, 2026-10-07).
                raise Refused(400, 'line_parent_change',
                              f'A line of {model_key} {obj.pk} cannot move to {line_data[key]}.',
                              {'line_id': line_data.get('id'), key: line_data[key]})
        for key in getattr(LineModel, 'HEADER_PARTY_FIELDS', ()):
            if key in line_data and not _same(line_data[key], getattr(obj, key, None)):
                # A line's party ids are its header's (Bill, 2026-09-23), refused like its
                # parent rather than silently replaced (Bill, 2026-10-10): change the header.
                raise Refused(400, 'line_party_derived',
                              f"A line's {key} is its {model_key}'s ({getattr(obj, key, None)}); "
                              f"change it on the {model_key}, not the line.",
                              {'line_id': line_data.get('id'), key: line_data[key]})
        _stamp_line_comments(line_data, actor)

        if _is_new_line(line_id):
            if carrier.delete:
                continue                       # never saved; nothing to delete
            line_obj = LineModel()
            if keep_uuid:
                line_obj.uuid = keep_uuid
            line_obj._actor = actor
            setattr(line_obj, f'{fk_field_name}_id', obj.pk)
            _copy_line_fields(line_obj, line_data, skip_fields, writable, merge=False,
                              model_key=model_key)
            if not getattr(line_obj, 'line_number', 0):
                line_obj.line_number = next_number
                next_number += 10
            _settle_new_line_item(line_obj, model_key)
            line_obj.save()
            new_line_ids.append(line_obj.pk)
            changed += 1
            continue

        line_obj = held.get(_as_pk(line_id))
        if line_obj is None:
            raise _line_not_found(line_id, model_key, obj.pk)
        line_obj._actor = actor

        # A removed line arrives marked (Bill, 2026-09-22); the backend deletes it, and the
        # line's post_delete writes the Pending that releases what it held.
        if carrier.delete:
            line_obj.delete()
            changed += 1
            continue
        if not carrier.dirty:
            continue

        sent_version = line_data.get('version')
        if sent_version is not None and not _same(sent_version, getattr(line_obj, 'version', None)):
            raise Refused(412, 'version_conflict',
                          f'Line {line_obj.pk} was changed by another save. Reload and try again.',
                          {'line_id': line_obj.pk, 'expected': sent_version,
                           'current': getattr(line_obj, 'version', None)})
        held_identity = _item_identity(line_obj)
        _copy_line_fields(line_obj, line_data, skip_fields, writable, merge=True,
                          model_key=model_key)
        _derive_item_fk(line_obj, line_data)
        _refuse_identity_change(line_obj, held_identity, model_key)
        line_obj.save()
        changed += 1

    if next_number != first_number and hasattr(obj, 'line_increment'):
        obj.line_increment = next_number
        obj.save(update_fields=['line_increment', 'version', 'dt_modified'])
    if changed:
        # After the commit (Fable, import plan): it called Celery apply_async inside the
        # transaction, so a rolled-back save — an import preview — still started a drain, and a
        # worker started before the commit would not see these rows (walkthrough stop 6).
        from django.db import transaction
        from apps.products.dispatch_pending import dispatch_pending_processing
        transaction.on_commit(lambda: dispatch_pending_processing(limit=200, caller='save_line_processing'))
    return new_line_ids


def _as_pk(line_id):
    try:
        return int(line_id)
    except (TypeError, ValueError):
        return line_id
