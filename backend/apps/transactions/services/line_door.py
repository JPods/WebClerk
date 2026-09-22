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
        # A count is an audit, not work: it commits nothing. What it finds reaches on_hand
        # when the line completes (Bill, 2026-09-20).
        return item_id, empty

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
                     {'active': loaded['active'], 'remaining': loaded['remaining']},
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


def _write(line, item_id: int, deltas: Dict[str, float], *, reason: str, layer=None) -> None:
    from apps.core.models import Pending

    changes: Dict[str, Any] = {'item_id': item_id, 'reason': reason, **deltas}
    if layer:
        changes['layer'] = layer
    Pending.objects.create(
        model_name='item',
        record_id=str(item_id),
        purpose='inventory_line_add',
        name=f"{line._meta.model_name} {line.pk}: {reason}"[:120],
        changes=changes,
        config={'line_id': line.pk, 'line_model': line._meta.model_name,
                'source_type': _header_model_name(line.parent) if line.parent else '',
                'source_id': getattr(line.parent, 'pk', None)},
    )


def post_line_change(line, *, deleted: bool = False) -> None:
    """The one door. Called from the line's save and from its post_delete receiver."""
    from apps.transactions.services.line_manage import _receipt_layer

    header = line.parent
    before_item, before = _snapshot_footprint(line, header)
    if deleted:
        after_item, after = before_item, {}
    else:
        after_item, after = _current_footprint(line)

    if before_item and after_item and before_item != after_item:
        # The item changed: the old one gives back everything, the new one takes what it holds.
        if before:
            _write(line, before_item, _difference(before, {}), reason='item changed away')
        if after:
            _write(line, after_item, _difference({}, after), reason='item changed to')
        return

    item_id = after_item or before_item
    deltas = _difference(before, after)
    if not item_id or not deltas:
        return

    layer = None
    if _header_model_name(header) == 'receipt' and deltas.get('on_hand'):
        # Received goods move a layer with them; a new line creates it, a change or a delete
        # moves the one the line already has.
        layer = _receipt_layer(line, header, create=not getattr(line, 'inventory_layer_id', None))

    reason = 'line deleted' if deleted else ('line added' if not before else 'line changed')
    _write(line, item_id, deltas, reason=reason, layer=layer)
