"""Spread a receipt's charges onto its lines: once on its own, after that only on command.

POST /wcapi/receipt/<id>/spread/      {} for every charge, or {"components": ["freight"]}

Bill, 2026-11-25: "The point to make to users changing a line's values is that it does not
recalculate other lines. If they wish to recalc, they should change at the receipt level and re-run
the spreader." A line's share of a charge is its own figure, cost.landed.<freight|duty|handling|vat>.

Bill, 2026-11-26: "Auto spread seems like a good idea. It is likely users will come up with
multiple options for this service, so Alice should be prepared and our code should allow
user-defined variations." So:

- **The first spread is automatic** (first_spread). The first time a charge stands on a receipt
  that has a received product line, it is divided over the lines by its basis, and the receipt
  records it: allocations.spread.<comp> = {dt, by, basis, basis_used, reason}. A charge named there
  is never spread by a save again; a later change to the charge, or a line added afterwards, shows
  as totals.unallocated until the person runs the command or types the shares.
- **The command** divides each charge named by its basis (allocations.method.<comp>: value,
  quantity or weight) in exact cents, replacing whatever the lines held, typed or not.
- **The variation the person owns** is the basis, per charge, per receipt. ``manual`` means nothing
  spreads that charge, neither the first time nor the command: every share is typed.
  allocations.spread is the record Alice reads to learn what a company does for a vendor or a kind
  of charge (readme 108 R8).
- **Like items on one receipt** is the recommendation (Bill, 2026-11-26). An item may carry a
  class for each charge (item.config.landed_class.<comp>, a label, blank for most). When the
  lines of a receipt carry different labels for a charge, the decision and the record name them
  (``classes``) and say so in ``reason``. It still spreads.

The lines are saved through the save door, so the totals follow and the received lines' layers
are re-costed (line_door.reconcile_receipt_layers). A journalized receipt is refused.

Answer: {spread: [{component, amount, basis, basis_used, reason}], unallocated: {...}}.
readmes/113-unallocated-charges-at-journalize.md
"""
from __future__ import annotations

import contextvars
import time
from typing import Any, Dict, List

from apps.core.services.door import Refused


#: Receipts being divided now. Dividing saves the receipt and its lines, and each of those saves
#: asks for the first spread again; the one under way answers for them.
_DIVIDING: contextvars.ContextVar[frozenset] = contextvars.ContextVar('receipt_dividing', default=frozenset())


def _divide(actor, receipt, wanted: List[str], by: str) -> List[Dict[str, Any]]:
    """Divide each charge in ``wanted`` over the receipt's product lines — the one place a spread
    is written. The lines are saved through the save door as the person; the record of the spread
    (allocations.spread) is the system's own note, written beside them, not a field a person
    edits. Returns the decisions, one per charge."""
    token = _DIVIDING.set(_DIVIDING.get() | {receipt.pk})
    try:
        return _divide_now(actor, receipt, wanted, by)
    finally:
        _DIVIDING.reset(token)


def _divide_now(actor, receipt, wanted: List[str], by: str) -> List[Dict[str, Any]]:
    from apps.core.services.save import save_record
    from apps.transactions.models import Receipt, ReceiptLine
    from apps.transactions.services.pricing.totals_compute import (
        MANUAL_BASIS, _d, recalculate_totals, spread_landed)

    recalculate_totals(receipt.pk, 'receipt')          # the lines' amounts as they stand
    lines = [l for l in ReceiptLine.objects.filter(receipt_id=receipt.pk).order_by('line_number', 'pk')
             if getattr(l, 'is_active', True) and (l.line_type or 'product') == 'product']
    goods = [(l, _d((l.quantity or {}).get('active', 0) or 0, places=6)) for l in lines]
    amounts = {id(l): _d((l.totals or {}).get('amount', 0) or 0) for l in lines}
    receipt.refresh_from_db()
    alloc = dict(receipt.allocations or {})
    methods = alloc.get('method') if isinstance(alloc.get('method'), dict) else {}

    shares = {l.pk: dict((l.cost or {}).get('landed') or {}) for l in lines}
    decisions, record = [], dict(alloc.get('spread') or {})
    now = int(time.time() * 1000)
    for comp in wanted:
        total = _d(alloc.get(comp, 0) or 0)
        basis = methods.get(comp) or 'value'
        if basis == MANUAL_BASIS:
            decision = {'component': comp, 'amount': float(total), 'basis': basis, 'basis_used': basis,
                        'reason': "manual: each line's share is typed"}
        else:
            if total and not goods:
                raise Refused(409, 'no_lines_to_carry',
                              f'This receipt has {comp} {total} and no product line to carry it. Add a line first.',
                              {'component': comp})
            try:
                parts, decision = spread_landed(comp, total, basis, goods, amounts)
            except Exception as e:                         # a basis that is not one of the three
                raise Refused(400, 'bad_basis', str(getattr(e, 'message', e)), {'component': comp})
            for (line, _qty), part in zip(goods, parts):
                shares[line.pk][comp] = float(part)
        mixed = _classes(lines, comp) if total else []
        if len(mixed) > 1:
            # Coaching, never a refusal (Bill, 2026-11-26): unlike items share this charge.
            decision['classes'] = mixed
            decision['reason'] = '; '.join(filter(None, [
                decision['reason'],
                f"lines carry different {comp} classes ({', '.join(mixed)}): one receipt for like "
                f"items spreads {comp} fairly"]))
        decisions.append(decision)
        record[comp] = {'dt': now, 'by': by, 'basis': decision['basis'],
                        'basis_used': decision['basis_used'], 'reason': decision['reason']}
        if len(mixed) > 1:
            record[comp]['classes'] = mixed

    Receipt.objects.filter(pk=receipt.pk).update(allocations={**alloc, 'spread': record})
    if lines:
        save_record(actor, {'id': receipt.pk, 'lines': [
            {'id': l.pk, 'cost': {**(l.cost or {}), 'landed': shares[l.pk]}} for l in lines]},
            model_key='receipt')
    return decisions


def _classes(lines, comp: str) -> List[str]:
    """The distinct labels the lines' items carry for this charge
    (item.config.landed_class.<comp>); blank is no label and is left out."""
    from apps.products.models import Item
    from apps.transactions.models.base_line_model import line_item_id
    ids = {i for i in (line_item_id(l) for l in lines) if i}
    labels = set()
    for config in Item.objects.filter(pk__in=ids).values_list('config', flat=True):
        label = str((((config or {}).get('landed_class') or {}).get(comp)) or '').strip()
        if label:
            labels.add(label)
    return sorted(labels)


def spread(ctx) -> Dict[str, Any]:
    from apps.transactions.models import ReceiptLine
    from apps.transactions.services.pricing.totals_compute import LANDED_COMPONENTS, receipt_unallocated

    receipt = ctx.obj
    if receipt.dt_journaled:
        raise Refused(409, 'receipt_journalized',
                      'This receipt is journalized: its charges have posted to the ledger and no '
                      'longer change.', {'receipt_id': receipt.pk})
    wanted = (ctx.data or {}).get('components') or list(LANDED_COMPONENTS)
    unknown = [c for c in wanted if c not in LANDED_COMPONENTS] if isinstance(wanted, list) else [wanted]
    if unknown or not isinstance(wanted, list):
        raise Refused(400, 'unknown_component',
                      f"components names charges to spread: {', '.join(LANDED_COMPONENTS)}.",
                      {'unknown': unknown})

    decisions = _divide(ctx.actor, receipt, wanted, 'command')
    receipt.refresh_from_db()
    left = receipt_unallocated(receipt, ReceiptLine.objects.filter(receipt_id=receipt.pk))
    return {'spread': decisions, 'unallocated': {k: float(v) for k, v in left.items()}}


def first_spread(receipt) -> None:
    """The automatic spread (Bill, 2026-11-26): each charge that stands on the receipt, has never
    been spread (no allocations.spread.<comp>) and is not manual is divided over the lines, once
    the receipt has a received product line to carry it. Done once per unit of work, after the
    document's lines are all saved, so a receipt saved with its lines divides over all of them.
    Outside a unit it happens now."""
    from apps.core.services import unit_of_work as uow

    receipt_id = receipt.pk
    if not receipt_id or receipt_id in _DIVIDING.get():
        return

    def work():
        from apps.core.services.door import Actor, acting_actor
        from apps.transactions.models import Receipt, ReceiptLine
        from apps.transactions.services.pricing.totals_compute import LANDED_COMPONENTS, MANUAL_BASIS, _d
        held = Receipt.objects.filter(pk=receipt_id, dt_journaled=0).first()
        if held is None or receipt_id in _DIVIDING.get():
            return                      # gone, or journalized: nothing spreads
        alloc = held.allocations if isinstance(held.allocations, dict) else {}
        methods = alloc.get('method') if isinstance(alloc.get('method'), dict) else {}
        done = alloc.get('spread') if isinstance(alloc.get('spread'), dict) else {}
        wanted = [comp for comp in LANDED_COMPONENTS
                  if _d(alloc.get(comp, 0) or 0) and comp not in done
                  and (methods.get(comp) or 'value') != MANUAL_BASIS]
        if not wanted:
            return
        received = any(float((l.quantity or {}).get('active') or 0) > 0
                       for l in ReceiptLine.objects.filter(receipt_id=receipt_id)
                       if getattr(l, 'is_active', True) and (l.line_type or 'product') == 'product')
        if not received:
            return                      # nothing has arrived to carry it; it waits
        _divide(acting_actor() or Actor.system(), held, wanted, 'auto')

    if not uow.defer(('receipt_first_spread', receipt_id), work):
        work()


def register() -> None:
    from apps.core.services.verbs import register_command
    register_command('receipt', 'spread', spread)
