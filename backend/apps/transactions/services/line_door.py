"""One door: every line save and every line delete writes one Pending, through this function.

Bill, 2026-09-22 (the WebClerk2 rule): "I had every save and every delete funnel through one
function. Each add or delete would trigger a dInventory record (our pending model). If a line is
deleted, it must behave just like an add, increase or decrease of inventory or cash." And:
"wcapi is intended to behave the same — one door to guard."

A line's **footprint** is what it holds of an item, as a pure function of the line as saved:

    commitment (on_qt / on_so / on_po / on_wo)  = quantity.remaining   (a quote's weighted)
    invoice                                     = on_in +active, on_hand −active
    receipt                                     = on_rc +active, on_hand +active
    a not-tracked item, or a count workorder     = nothing at all

The door writes `after − before`. An add is `before = {}`, a delete is `after = {}`, and a change
is the subtraction — which is why a delete behaves exactly like an add in reverse, with no delete
path of its own. "Before" comes from the line's loaded snapshot (Bill's WC2 collection of initial
line values), held for the whole save so every receiver reads the same one.

The delete half is a post_delete receiver, not an override of delete(): a header's CASCADE removes
its lines without ever calling Line.delete().
~/Allie/readmes/assessments/2026-09-22-one-door-line-pendings.md
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

#: header model name → the bucket its lines commit
PENDING_TYPE_BUCKET: Dict[str, str] = {
    'quote': 'on_qt',
    'order': 'on_so',
    'purchase': 'on_po',
    'workorder': 'on_wo',
    'invoice': 'on_in',
    'receipt': 'on_rc',
}

BUCKETS = ('on_qt', 'on_so', 'on_po', 'on_wo', 'on_in', 'on_rc', 'on_hand')

Footprint = Tuple[Optional[int], Dict[str, float]]


def _header_model_name(header) -> str:
    return (getattr(header, 'model_name', None) or header._meta.model_name or '').lower()


def _is_tracked(item_id: Optional[int]) -> bool:
    """A not-tracked item (labor, freight) holds no stock: its lines are cost, not stock."""
    from apps.products.models import Item
    if not item_id:
        return False
    item = Item.objects.filter(pk=item_id).only('id', 'flags').first()
    return item is not None and not item.is_not_tracked


def footprint(item_id: Optional[int], quantity: Dict[str, Any], header, line=None) -> Footprint:
    """What a line with these values holds of this item. Values, not the line object, so the
    same function reads the loaded snapshot and the instance being saved."""
    from apps.transactions.models.base_line_model import forecast_probability

    empty: Dict[str, float] = {}
    if not item_id or header is None:
        return item_id, empty

    bucket = PENDING_TYPE_BUCKET.get(_header_model_name(header))
    if bucket is None or not _is_tracked(item_id):
        return item_id, empty

    if _header_model_name(header) == 'workorder' and getattr(header, 'kind', '') == 'count':
        # A correction (plan §16b; supersedes 2026-09-20's "commits nothing"): a count line
        # holds the variance against the book taken when it was first saved (staged, set by
        # the line, never the caller); an adjust line holds its change. Each save's Pending is
        # the difference, so a re-count posts only what moved.
        line_type = getattr(line, 'line_type', None) if line is not None else None
        active = float(quantity.get('active') or 0)
        if line_type == 'count':
            held = round(active - float(quantity.get('staged') or 0), 6)
        elif line_type == 'adjust':
            held = active
        else:
            return item_id, empty
        return item_id, ({'on_hand': held} if held else empty)

    active = float(quantity.get('active') or 0)
    remaining = quantity.get('remaining')
    remaining = active if remaining is None else float(remaining)

    held: Dict[str, float] = {}
    if bucket == 'on_in':                       # an invoice issues goods
        held['on_in'] = active
        held['on_hand'] = -active
    elif bucket == 'on_rc':                     # a receipt puts them on the shelf
        held['on_rc'] = active
        held['on_hand'] = active
        # on_po is NOT released here: receiving drops the purchase line's remaining, and that
        # line's own door releases its commitment. Claiming it here released it twice.
    else:                                       # a commitment follows what is left to fill
        weight = forecast_probability(header) if bucket == 'on_qt' else 1.0
        held[bucket] = remaining * weight

    return item_id, {k: v for k, v in held.items() if v}


def _snapshot_footprint(line, header) -> Footprint:
    """The line as it was loaded. No snapshot (a new line, or one built in memory) holds nothing."""
    loaded = getattr(line, '_loaded', None)
    if not loaded:
        return None, {}
    return footprint(loaded['item_id'],
                     {'active': loaded['active'], 'remaining': loaded['remaining'],
                      'staged': loaded.get('staged')},
                     header, line)


def _current_footprint(line) -> Footprint:
    from apps.transactions.models.base_line_model import line_item_id
    header = line.parent
    quantity = line.quantity if isinstance(line.quantity, dict) else {}
    return footprint(line_item_id(line), quantity, header, line)


def _difference(before: Dict[str, float], after: Dict[str, float]) -> Dict[str, float]:
    return {b: round(after.get(b, 0.0) - before.get(b, 0.0), 6)
            for b in BUCKETS
            if round(after.get(b, 0.0) - before.get(b, 0.0), 6)}


#: lines that keep an events[] — one event per Pending applied to them (plan §16c/§16d);
#: a workorder line's commitment Pendings carry none (its events are its completions)
EVENT_LINES = ('invoiceline', 'receiptline')
CORRECTION_TYPES = ('count', 'adjust')


def is_correction(line) -> bool:
    """A count or adjust line of a count workorder: stock corrected through the door (§16b)."""
    header = getattr(line, 'parent', None)
    return (line._meta.model_name == 'workorderline' and header is not None
            and getattr(header, 'kind', '') == 'count'
            and getattr(line, 'line_type', None) in CORRECTION_TYPES)


def _reason(line) -> str:
    """An adjust line's reason: the newest comments.process entry (Bill, 2026-09-26)."""
    comments = line.comments if isinstance(getattr(line, 'comments', None), dict) else {}
    entries = [e for e in (comments.get('process') or []) if isinstance(e, dict) and (e.get('mgs') or '').strip()]
    return entries[-1]['mgs'].strip() if entries else ''


def _by(line):
    actor = getattr(line, '_actor', None)
    if actor is None:
        return None
    user = getattr(actor, 'user', None)
    return getattr(user, 'pk', None) or f"{actor.kind}:{getattr(actor, 'source', '')}"


def _write(line, item_id: int, deltas: Dict[str, float], *, reason: str, layer=None) -> None:
    import time
    import uuid
    from apps.core.models import Pending

    changes: Dict[str, Any] = {'item_id': item_id, 'reason': reason, **deltas}
    if layer:
        changes['layer'] = layer
    config = {'line_id': line.pk, 'line_model': line._meta.model_name,
              'source_type': _header_model_name(line.parent) if line.parent else '',
              'source_id': getattr(line.parent, 'pk', None)}
    event = None
    if line._meta.model_name in EVENT_LINES and deltas.get('on_hand'):
        # The applier appends this to the line's events[] in the apply that moves the stock,
        # with what the layers gave (consumed) filled in there.
        event = {'id': uuid.uuid4().hex, 'kind': reason, 'dt': int(time.time() * 1000),
                 'by': _by(line), 'qty': deltas['on_hand']}
    elif is_correction(line):
        # The count's evidence, even when nothing moved (a zero variance proves the count).
        quantity = line.quantity if isinstance(line.quantity, dict) else {}
        physical = line.physical if isinstance(getattr(line, 'physical', None), dict) else {}
        event = {'id': uuid.uuid4().hex, 'kind': line.line_type, 'dt': int(time.time() * 1000),
                 'by': _by(line), 'qty': deltas.get('on_hand', 0.0), 'reason': _reason(line),
                 'warehouse_id': _warehouse_of(line, line.parent), 'layer_id': physical.get('layer_id')}
        if line.line_type == 'count':
            event.update(book=float(quantity.get('staged') or 0), counted=float(quantity.get('active') or 0))
            event['variance'] = round(event['counted'] - event['book'], 6)
    if event:
        config['event'] = event
    Pending.objects.create(
        model_name='item',
        record_id=str(item_id),
        purpose='inventory_line_add',
        name=f"{line._meta.model_name} {line.pk}: {reason}"[:120],
        changes=changes,
        config=config,
    )


def _warehouse_of(line, header) -> Optional[int]:
    """Where a line's goods leave or land. The warehouse feature is set aside until the joint
    review (Bill, 2026-09-26; action 31277, due 2026-12-26): stock runs as one warehouse, so this
    names none and sales consume from any layer. The fields stay (physical.warehouse_id,
    shipping.warehouse_id); nothing reads them until the review decides what they mean."""
    return None


def _stock_warehouse(line) -> int:
    """Where stock that arrives on a line lands (a return, found stock): the default warehouse,
    the first active one, while the warehouse feature is set aside."""
    from apps.core.services.door import Refused
    from apps.products.models.warehouse import Warehouse
    warehouse_id = Warehouse.objects.filter(is_active=True).order_by('id').values_list('id', flat=True).first()
    if warehouse_id is None:
        raise Refused(400, 'no_warehouse', 'Stock has nowhere to land: add a warehouse first.',
                      {'line_id': line.pk})
    return warehouse_id


def _invoice_layer_specs(line, header, before_active: float, after_active: float) -> list:
    """What an invoice line's change does to the layers (plan §16d), in the order to apply.

    A positive line sells: more consumes by the item's costing method, less gives back to the
    layers this line consumed. A negative line is a return: it lands in a layer of its own at
    the item's average cost, and a smaller return takes that layer back down. A line crossing
    zero does both.
    """
    specs = []
    # What this line has had done to its layers so far, carried with a give-back: a deleted
    # line is gone before its Pending applies, so the applier cannot read it then.
    history = [e['consumed'] for e in (getattr(line, 'events', None) or [])
               if isinstance(e, dict) and isinstance(e.get('consumed'), dict)]
    sold = round(max(after_active, 0) - max(before_active, 0), 6)
    if sold > 0:
        specs.append({'consume': sold, 'warehouse_id': _warehouse_of(line, header)})
    elif sold < 0:
        specs.append({'give_back': -sold, 'history': history})
    returned = round(max(-after_active, 0) - max(-before_active, 0), 6)
    if returned > 0:
        specs.append({'return': returned, 'warehouse_id': _stock_warehouse(line)})
    elif returned < 0:
        specs.append({'return_shrink': -returned, 'history': history})
    return specs


def _correction_layer_specs(line, header, before: float, after: float) -> list:
    """What a count/adjust line's change does to the layers: found stock lands in a layer of the
    line's own at the line's unit cost (zero allowed); missing stock comes off the layer the line
    names, else by the item's costing method. Less found shrinks the line's own layer; less
    missing gives back to the layers it took."""
    history = [e['consumed'] for e in (getattr(line, 'events', None) or [])
               if isinstance(e, dict) and isinstance(e.get('consumed'), dict)]
    physical = line.physical if isinstance(getattr(line, 'physical', None), dict) else {}
    specs = []
    found = round(max(after, 0) - max(before, 0), 6)
    if found > 0:
        warehouse_id = _stock_warehouse(line)
        cost = line.cost if isinstance(getattr(line, 'cost', None), dict) else {}
        specs.append({'found': found, 'warehouse_id': warehouse_id,
                      'unit_cost': float(cost.get('unit') or 0)})
    elif found < 0:
        specs.append({'found_shrink': -found, 'history': history})
    missing = round(max(-after, 0) - max(-before, 0), 6)
    if missing > 0:
        specs.append({'consume': missing, 'warehouse_id': _warehouse_of(line, header),
                      'layer_id': physical.get('layer_id')})
    elif missing < 0:
        specs.append({'give_back': -missing, 'history': history})
    return specs


def _refuse_correction(line, *, deleted: bool) -> None:
    """What a correction line may not be (plan §16b/§16c)."""
    from apps.core.services.door import Refused
    header = line.parent
    if header is None or _header_model_name(header) != 'workorder' or getattr(header, 'kind', '') != 'count':
        return
    if deleted:
        if is_correction(line) and any(isinstance(e, dict) for e in (line.events or [])):
            raise Refused(409, 'count_recorded',
                          f"Line {line.pk} has moved stock and is the record of it; it cannot be deleted. "
                          "Count again, or add an adjust line with its reason.", {'line_id': line.pk})
        return
    if getattr(line, 'line_type', None) not in CORRECTION_TYPES:
        raise Refused(400, 'count_line_type',
                      "A count workorder's lines are line_type 'count' (what was counted) or "
                      "'adjust' (a change, with its reason in comments.process).", {'line_id': line.pk})
    from apps.transactions.models.base_line_model import line_item_id
    if not _is_tracked(line_item_id(line)):
        raise Refused(400, 'item_not_tracked', 'This item holds no stock (not tracked); it cannot be counted.',
                      {'line_id': line.pk})
    if line.line_type == 'adjust' and not _reason(line):
        raise Refused(400, 'reason_required',
                      'An adjust line needs its reason: add a comments.process entry saying why.',
                      {'line_id': line.pk})
    if hasattr(line, '_actor') and line._actor is None:
        raise Refused(403, 'counter_required', 'A correction needs the person responsible; sign in.',
                      {'line_id': line.pk})


def post_line_change(line, *, deleted: bool = False) -> None:
    """The one door. Called from the line's save and from its post_delete receiver."""
    from apps.transactions.services.line_manage import _receipt_layer

    _refuse_correction(line, deleted=deleted)
    header = line.parent
    before_item, before = _snapshot_footprint(line, header)
    if deleted:
        after_item, after = before_item, {}
    else:
        after_item, after = _current_footprint(line)

    is_invoice = _header_model_name(header) == 'invoice' if header is not None else False
    loaded = getattr(line, '_loaded', None) or {}
    before_active = float(loaded.get('active') or 0) if before else 0.0
    quantity = line.quantity if isinstance(line.quantity, dict) else {}
    after_active = 0.0 if deleted else float(quantity.get('active') or 0)

    if before_item and after_item and before_item != after_item:
        # The item changed: the old one gives back everything, the new one takes what it holds.
        # A receipt's old layer comes down by its own id; the new item gets a layer of its own.
        is_receipt = _header_model_name(header) == 'receipt'
        old_layer = getattr(line, 'inventory_layer_id', None)
        if before:
            layer = (_invoice_layer_specs(line, header, before_active, 0.0) if is_invoice
                     else {'layer_id': old_layer} if is_receipt and old_layer else None)
            _write(line, before_item, _difference(before, {}), reason='item changed away', layer=layer)
        if after:
            layer = (_invoice_layer_specs(line, header, 0.0, after_active) if is_invoice
                     else _receipt_layer(line, header, create=True) if is_receipt else None)
            _write(line, after_item, _difference({}, after), reason='item changed to', layer=layer)
        return

    item_id = after_item or before_item
    deltas = _difference(before, after)
    correction = is_correction(line)
    if correction and item_id and not deltas and not deleted and getattr(line, '_loaded', None) is None:
        # A first count that matches the book still leaves its record: the count happened.
        # Only a line never saved before (no loaded snapshot) — the applier's own event save
        # re-saves the line, and a zero variance has no footprint then either (§16a.2).
        _write(line, item_id, {}, reason=line.line_type)
        return
    if not item_id or not deltas:
        return
    layer = None
    if correction and deltas.get('on_hand'):
        layer = _correction_layer_specs(line, header, before.get('on_hand', 0.0), after.get('on_hand', 0.0))
    elif is_invoice and deltas.get('on_hand'):
        layer = _invoice_layer_specs(line, header, before_active, after_active)
    elif _header_model_name(header) == 'receipt' and deltas.get('on_hand'):
        # Received goods move a layer with them; a new line creates it, a change or a delete
        # moves the one the line already has.
        layer = _receipt_layer(line, header, create=not getattr(line, 'inventory_layer_id', None))

    reason = (line.line_type if correction and not deleted
              else 'line deleted' if deleted else ('line added' if not before else 'line changed'))
    _write(line, item_id, deltas, reason=reason, layer=layer)
