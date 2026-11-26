"""Spread a receipt's charges onto its lines — on command, never by a save (Bill, 2026-11-25).

POST /wcapi/receipt/<id>/spread/      {} for every charge, or {"components": ["freight"]}

Bill: "The point to make to users changing a line's values is that it does not recalculate other
lines. If they wish to recalc, they should change at the receipt level and re-run the spreader."
A line's share of a charge is its own figure, cost.landed.<freight|duty|handling|vat>. This command
is the one thing that writes every line's share at once: each charge named is divided over the
receipt's product lines by its basis (allocations.method.<comp>: value, quantity or weight) in
exact cents, replacing whatever the lines held, typed or not. The lines are saved through the
save door, so the totals follow and the received lines' layers are re-costed
(line_door.reconcile_receipt_layers). A journalized receipt is refused.

Answer: {spread: [{component, amount, basis, basis_used, reason}], unallocated: {...}}.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict

from apps.core.services.door import Refused


def spread(ctx) -> Dict[str, Any]:
    from apps.core.services.save import save_record
    from apps.transactions.models import ReceiptLine
    from apps.transactions.services.pricing.totals_compute import (
        LANDED_COMPONENTS, _d, receipt_unallocated, recalculate_totals, spread_landed)

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

    recalculate_totals(receipt.pk, 'receipt')          # the lines' amounts as they stand
    lines = [l for l in ReceiptLine.objects.filter(receipt_id=receipt.pk).order_by('line_number', 'pk')
             if getattr(l, 'is_active', True) and (l.line_type or 'product') == 'product']
    goods = [(l, _d((l.quantity or {}).get('active', 0) or 0, places=6)) for l in lines]
    amounts = {id(l): _d((l.totals or {}).get('amount', 0) or 0) for l in lines}
    alloc = receipt.allocations or {}
    methods = alloc.get('method') if isinstance(alloc.get('method'), dict) else {}

    shares = {l.pk: dict((l.cost or {}).get('landed') or {}) for l in lines}
    decisions = []
    for comp in wanted:
        total = _d(alloc.get(comp, 0) or 0)
        if total and not goods:
            raise Refused(409, 'no_lines_to_carry',
                          f'This receipt has {comp} {total} and no product line to carry it. Add a line first.',
                          {'component': comp})
        try:
            parts, decision = spread_landed(comp, total, methods.get(comp) or 'value', goods, amounts)
        except Exception as e:                         # a basis that is not one of the three
            raise Refused(400, 'bad_basis', str(getattr(e, 'message', e)), {'component': comp})
        decisions.append(decision)
        for (line, _qty), part in zip(goods, parts):
            shares[line.pk][comp] = float(part)

    if lines:
        save_record(ctx.actor, {'id': receipt.pk, 'lines': [
            {'id': l.pk, 'cost': {**(l.cost or {}), 'landed': shares[l.pk]}} for l in lines]},
            model_key='receipt')
    receipt.refresh_from_db()
    left = receipt_unallocated(receipt, ReceiptLine.objects.filter(receipt_id=receipt.pk))
    return {'spread': decisions, 'unallocated': {k: float(v) for k, v in left.items()}}


def register() -> None:
    from apps.core.services.verbs import register_command
    register_command('receipt', 'spread', spread)
