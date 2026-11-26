"""Spread a receipt's charges onto its lines — on command, never by a save.

POST /wcapi/receipt/<id>/spread/      {} for every charge, or {"components": ["freight"]}

Bill, 2026-11-25: "The point to make to users changing a line's values is that it does not
recalculate other lines. If they wish to recalc, they should change at the receipt level and re-run
the spreader." A line's share of a charge is its own figure, cost.landed.<freight|duty|handling|vat>.

Bill, 2026-11-26: "let's switch the auto spreading to a button. So users see what we are doing."
Nothing spreads on its own, not even the first time (an automatic first spread was built and
withdrawn the same day). The receipt's Spread button runs this command and the answer says, charge
by charge, what was divided and by what basis (``messages``).

- **The command** divides each charge named by its basis (allocations.method.<comp>: value,
  quantity or weight) in exact cents, replacing whatever the lines held, typed or not, and records
  it on the receipt: allocations.spread.<comp> = {dt, by, basis, basis_used, reason}.
- **The variation the person owns** is the basis, per charge, per receipt (Bill, 2026-11-26: "our
  code should allow user-defined variations"). ``manual`` means the command leaves that charge
  alone: every share is typed. allocations.spread is the record Alice reads to learn what a
  company does for a vendor or a kind of charge (readme 108 R8).
- **Like items on one receipt** is the recommendation (Bill, 2026-11-26). An item may carry a
  class for each charge (item.config.landed_class.<comp>, a label, blank for most). When the
  lines of a receipt carry different labels for a charge, the decision and the record name them
  (``classes``) and say so in ``reason``. It still spreads.

The lines are saved through the save door, so the totals follow and the received lines' layers
are re-costed (line_door.reconcile_receipt_layers). A journalized receipt is refused.

Answer: {spread: [{component, amount, basis, basis_used, reason}], unallocated: {...}, messages: [...]}.
readmes/113-unallocated-charges-at-journalize.md
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

from apps.core.services.door import Refused


def _divide(actor, receipt, wanted: List[str], by: str) -> List[Dict[str, Any]]:
    """Divide each charge in ``wanted`` over the receipt's product lines — the one place a spread
    is written. The lines are saved through the save door as the person; the record of the spread
    (allocations.spread) is the system's own note, written beside them, not a field a person
    edits. Returns the decisions, one per charge."""
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
    return {'spread': decisions, 'unallocated': {k: float(v) for k, v in left.items()},
            'messages': [_said(d) for d in decisions if d['amount']]}


def _said(decision: Dict[str, Any]) -> str:
    """One charge, as the person reads it after pressing Spread."""
    comp, amount = decision['component'], decision['amount']
    if decision['basis_used'] == 'manual':
        return f"{comp} {amount:,.2f} left as typed (manual)"
    text = f"{comp} {amount:,.2f} spread by {decision['basis_used']}"
    return f"{text} ({decision['reason']})" if decision['reason'] else text


def register() -> None:
    from apps.core.services.verbs import register_command
    register_command('receipt', 'spread', spread)
