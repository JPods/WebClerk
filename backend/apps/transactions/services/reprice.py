"""Reprice a document's lines when its party or price level changes (readme 106 rule 5).

Bill, 2026-11-07: "if there are lines already built into a quote at retail pricing, assigning
a customer that is wholesale price_level would update the quote to that customer's settings
and be returned from the backend." Lines were priced only when added (line_manage); this
prices them again, in the document's after_save, through the one sell-side pricing behaviour
(price_resolver.resolve_price, which also knows the customer's catalogs).

It fires when ``customer`` or ``price_level`` is in what the save changed — never at a
conversion's birth, whose lines come priced from the source. A line keeps its price when a
person fixed it (price.is_fixed, or quantity.is_fixed which locks the rates), or when a child
document already took some of it (quantity.remaining < quantity.active, or is_complete).
A locked document never gets here: the lock refuses the party change in the before hook.

The save answers with what happened, as structured detail in the hook's messages:
``{'repriced': [{line, line_number, item, old, new, resolved_by, below_margin_floor}],
'kept': [{line, line_number, why}], 'price_level': …}`` — the form says "N lines repriced to
wholesale". A price below the margin floor is flagged as every committed price is
(flag_below_margin: an Action, never a block).
"""
from __future__ import annotations

from typing import Any, Dict, List

#: The header fields whose change reprices the lines.
REPRICE_ON = frozenset({'customer', 'price_level'})


def reprice_lines(ctx) -> Dict[str, Any] | None:
    """The document's after_save: reprice its sell lines; the detail appended to ctx.messages."""
    obj = ctx.obj
    if not hasattr(obj, 'price_level') or not hasattr(obj, 'customer_id') or not hasattr(obj, 'lines'):
        return None                                   # not a sell-side document
    if not (REPRICE_ON & set(ctx.changed)):
        return None
    if not ctx.is_update and getattr(obj, 'parent_id', None):
        return None                                   # a conversion's birth: priced by its source
    from apps.products.services.price_resolver import flag_below_margin, resolve_price
    from apps.transactions.models.base_line_model import line_item_id
    repriced: List[Dict[str, Any]] = []
    kept: List[Dict[str, Any]] = []
    for line in obj.lines.all().order_by('line_number', 'pk'):
        price = line.price if isinstance(line.price, dict) else {}
        qty = line.quantity if isinstance(line.quantity, dict) else {}
        why = _kept_why(price, qty)
        if why:
            kept.append({'line': line.pk, 'line_number': line.line_number, 'why': why})
            continue
        item_id = line.item_fk_id or line_item_id(line)   # the FK, else the item envelope's id
        if not item_id:
            continue                                  # a note or a charge: nothing to resolve
        active = float(qty.get('active') or 0) or 1
        result = resolve_price(item_id, customer_id=obj.customer_id, qty=active, level=obj.price_level)
        old, new = float(price.get('unit') or 0), float(result.price)
        if abs(old - new) < 1e-9 and (line.price_level or '') == (obj.price_level or ''):
            continue
        line.price = {**price, 'unit': new}             # unit is the input; the rest is derived
        line.price_level = obj.price_level
        line.save()
        flag_below_margin(item_id, result, obj.customer_id)
        item_env = line.item if isinstance(line.item, dict) else {}
        repriced.append({'line': line.pk, 'line_number': line.line_number,
                         'item': item_env.get('ida_item') or item_env.get('ida') or item_id,
                         'old': old, 'new': new, 'resolved_by': result.resolved_by,
                         'below_margin_floor': result.below_margin_floor})
    if not repriced and not kept:
        return None
    detail = {'repriced': repriced, 'kept': kept, 'price_level': obj.price_level or ''}
    ctx.messages.append(detail)
    return detail


def _kept_why(price: Dict[str, Any], qty: Dict[str, Any]) -> str:
    if price.get('is_fixed') or qty.get('is_fixed'):
        return 'fixed'
    if qty.get('is_complete'):
        return 'complete'
    remaining, active = qty.get('remaining'), qty.get('active')
    if remaining is not None and active is not None and float(remaining) < float(active):
        return 'consumed'                             # a child document took some of it
    return ''
