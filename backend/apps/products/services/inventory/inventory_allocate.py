"""Allocation — a person's decision, recorded (Bill, 2026-09-19).

> "We usually made allocate a manual function with sales people looking at on_hand,
> available, and on_so to make decisions. On order did not allocate."

`allocated` is entered, never derived. No document moves it: not a quote, not an order,
not goods on order. A salesperson reads on_hand, available and on_so and decides which
goods are set aside for whom; `available = on_hand − allocated` follows from that.

Every allocation is a movement like any other, so it travels the same pending path and
carries who, when and why.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from django.apps import apps as dj_apps
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


def _move(item_id: int, delta: Decimal, *, acted_by: str, reason: str,
          order_id: Optional[int], verb: str) -> Dict[str, Any]:
    Item = dj_apps.get_model('products', 'Item')
    Pending = dj_apps.get_model('core', 'Pending')
    if not acted_by:
        raise ValidationError({'acted_by': 'an allocation records who made it'})
    item = Item.objects.filter(pk=item_id).only('quantity', 'name').first()
    if item is None:
        raise ValidationError({'item_id': f'item {item_id} not found'})

    quantity = item.quantity or {}
    on_hand = Decimal(str(quantity.get('on_hand') or 0))
    allocated = Decimal(str(quantity.get('allocated') or 0))
    wanted = allocated + delta
    if wanted < 0:
        raise ValidationError({'qty': f'cannot release {abs(delta)} — only {allocated} is allocated'})
    if wanted > on_hand:
        raise ValidationError({'qty': f'cannot allocate {wanted} — only {on_hand} on hand'})

    Pending.objects.create(
        model_name='item',
        record_id=str(item_id),
        purpose='allocation',
        name=f"{verb} {abs(delta)} of item {item_id}",
        changes={'allocated': float(delta)},
        config={'item_id': item_id, 'source_type': 'allocation', 'source_id': order_id,
                'by': acted_by, 'reason': reason, 'verb': verb},
    )
    item.refresh_from_db()
    quantity = item.quantity or {}
    logger.info("[allocate] %s %s of item %s by %s (%s)", verb, abs(delta), item_id, acted_by, reason)
    return {'item_id': item_id, 'verb': verb, 'qty': float(abs(delta)),
            'allocated': float(quantity.get('allocated') or 0),
            'available': float(quantity.get('available') or 0),
            'on_hand': float(quantity.get('on_hand') or 0)}


def allocate(item_id: int, qty, *, acted_by: str, reason: str = '',
             order_id: Optional[int] = None) -> Dict[str, Any]:
    """Set goods aside. Never more than is on hand."""
    delta = Decimal(str(qty))
    if delta <= 0:
        raise ValidationError({'qty': 'allocate a positive quantity; use release to give it back'})
    return _move(item_id, delta, acted_by=acted_by, reason=reason, order_id=order_id, verb='allocate')


def release(item_id: int, qty, *, acted_by: str, reason: str = '',
            order_id: Optional[int] = None) -> Dict[str, Any]:
    """Give allocated goods back. Never more than is allocated."""
    delta = Decimal(str(qty))
    if delta <= 0:
        raise ValidationError({'qty': 'release a positive quantity'})
    return _move(item_id, -delta, acted_by=acted_by, reason=reason, order_id=order_id, verb='release')


def allocation_history(item_id: int, limit: int = 50) -> list[dict]:
    """Who allocated what, and when — read from the pendings themselves."""
    Pending = dj_apps.get_model('core', 'Pending')
    rows = (Pending.objects.filter(model_name='item', record_id=str(item_id), purpose='allocation')
            .order_by('-dt_created')[:limit])
    return [{'dt': r.dt_created, 'by': (r.config or {}).get('by'),
             'reason': (r.config or {}).get('reason'), 'verb': (r.config or {}).get('verb'),
             'qty': abs(float((r.changes or {}).get('allocated') or 0)),
             'order_id': (r.config or {}).get('source_id'),
             'applied': bool(r.dt_processed)} for r in rows]


__all__ = ['allocate', 'release', 'allocation_history']


# ── the commands: POST /wcapi/item/<id>/allocate/ and /release/ ───────

def _command(verb):
    def base(ctx) -> Dict[str, Any]:
        """{qty, reason?, order_id?} — who is the actor; the item is the command's record."""
        from apps.core.services.door import Refused
        who = (getattr(ctx.user, 'email', None) or ctx.actor.describe()) if ctx.user else \
            ctx.actor.describe()
        try:
            return (allocate if verb == 'allocate' else release)(
                ctx.obj.pk, ctx.data.get('qty'), acted_by=who,
                reason=ctx.data.get('reason') or '', order_id=ctx.data.get('order_id'))
        except ValidationError as e:
            details = getattr(e, 'message_dict', None) or {'qty': e.messages}
            raise Refused(400, f'{verb}_refused', '; '.join(
                f'{k}: {" ".join(map(str, v))}' for k, v in details.items()), details)
    return base


def register() -> None:
    """Allocation is a person's manual isolation of stock: available = on_hand − allocated
    (Bill, 2026-09-19 and 2026-09-24)."""
    from apps.core.services.verbs import register_command
    register_command('item', 'allocate', _command('allocate'))
    register_command('item', 'release', _command('release'))
