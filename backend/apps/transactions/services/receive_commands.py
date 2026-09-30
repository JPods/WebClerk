"""POST /wcapi/receipt/<id>/receive/ {lines?: [{line_id, qty?}]} — the goods go on the shelf.

Bill, 2026-09-30: goods are received when the receipt is issued against a purchase, as a step
of its own; journalizing comes later. And 2026-09-28: a layer never re-costs. So a planned
receipt holds its goods as staged (purchase→receipt convert), and receiving is the one moment a
receipt line's stock moves:

1. each line's received quantity is set (``quantity.active``), here and nowhere else
   (``ReceiptLine.save`` refuses it from a request);
2. the receipt's totals are computed for those quantities, so the landed shares exist;
3. each line's stock Pending is written through the line door's writer with its landed cost in
   the layer spec, so the layer is born at the receipt's final cost and never changes after.

``lines`` names the lines affected (the same rule as convert): only those, each at the qty given
or else what it has planned and not received. A qty above the plan is accepted and flagged to
Alice, as an over-shipment is.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction

from apps.core.services.door import Refused


def _refuse(code: str, message: str, details=None):
    return Refused(400, code, message, details if details is not None else {})


def _named(rows) -> Optional[Dict[int, Optional[float]]]:
    if rows in (None, ''):
        return None
    if not isinstance(rows, list) or not rows:
        raise _refuse('lines_required', 'Name the lines to receive: "lines": [{"line_id", "qty"?}].')
    wanted: Dict[int, Optional[float]] = {}
    for row in rows:
        if not isinstance(row, dict) or row.get('line_id') in (None, ''):
            raise _refuse('line_id_required', 'Each line names its "line_id".')
        qty = row.get('qty')
        if qty not in (None, ''):
            try:
                qty = float(qty)
            except (TypeError, ValueError):
                raise _refuse('bad_qty', f'Line {row["line_id"]}: "{qty}" is not a quantity.')
            if qty <= 0:
                raise _refuse('qty_not_positive',
                              f'Line {row["line_id"]}: receive a quantity above 0 ({qty:g} was asked).')
        wanted[int(row['line_id'])] = None if qty in (None, '') else qty
    return wanted


@transaction.atomic
def receive_receipt(receipt, *, actor=None, lines=None) -> Dict[str, Any]:
    """Receive a receipt's planned goods (all, or the lines named). Returns what was received."""
    from apps.transactions.behaviours import flag_over_receipts
    from apps.transactions.models import ReceiptLine
    from apps.transactions.models.base_line_model import line_item_id
    from apps.transactions.services.line_door import _is_tracked
    from apps.transactions.services.line_manage import _receipt_layer
    from apps.transactions.services.pricing.totals_compute import landed_layer_cost, recalculate_totals
    from apps.transactions.services.workorder_bom import _apply

    if receipt.dt_journaled:
        raise Refused(409, 'journalized', f'Receipt {receipt.ida or receipt.pk} is journalized; '
                      'receive against a new receipt.', receipt.pk)
    wanted = _named(lines)
    rows = list(ReceiptLine.objects.select_for_update().filter(receipt_id=receipt.pk).order_by('line_number', 'pk'))
    if wanted is not None:
        unknown = sorted(set(wanted) - {r.pk for r in rows})
        if unknown:
            raise _refuse('line_not_on_receipt', f'Lines {unknown} are not on this receipt.', {'line_ids': unknown})

    targets: List[Tuple[Any, float]] = []
    for line in rows:
        if wanted is not None and line.pk not in wanted:
            continue
        q = line.quantity if isinstance(line.quantity, dict) else {}
        active, staged = float(q.get('active') or 0), float(q.get('staged') or 0)
        qty = wanted.get(line.pk) if wanted else None
        qty = round(staged - active, 6) if qty is None else qty
        if qty <= 0:
            continue
        targets.append((line, qty))
    if not targets:
        raise _refuse('nothing_to_receive', 'Nothing is planned and not yet received on these lines.',
                      receipt.pk)

    # 1. The received quantity. The stock Pending in step 3 is the door's write for it, so the
    #    line's own save (and its door) does not run here.
    for line, qty in targets:
        q = dict(line.quantity or {})
        active = round(float(q.get('active') or 0) + qty, 6)
        q.update(active=active, staged=max(float(q.get('staged') or 0), active), remaining=0)
        ReceiptLine.objects.filter(pk=line.pk).update(quantity=q)

    # 2. The landed shares for what is now received.
    recalculate_totals(receipt.pk, 'receipt')

    # 3. Each line's stock; its layer is born at the line's final landed cost.
    received = []
    for line, qty in targets:
        line.refresh_from_db()
        line._actor = actor
        item_id = line_item_id(line)
        if not _is_tracked(item_id):
            received.append({'line_id': line.pk, 'qty': qty, 'layer_id': None})
            continue
        spec = _receipt_layer(line, receipt, create=True)
        spec['create']['landed'] = landed_layer_cost(line.totals, (line.quantity or {}).get('active')) or {}
        _apply(line, item_id, {'on_rc': qty, 'on_hand': qty}, reason='receive', layer=spec)
        received.append({'line_id': line.pk, 'qty': qty, 'layer_id': line.inventory_layer_id})

    # The purchase lines' remaining drops now, and each one's own door releases its on_po
    # (the post_save receiver that does this for a line save does not run: no line was saved).
    from apps.transactions.services.line_parent import refresh_parent_line
    for parent_line_id in sorted({line.parent_line_id for line, _ in targets if line.parent_line_id}):
        refresh_parent_line('receiptline', parent_line_id)
    flag_over_receipts(receipt)
    return {'id': receipt.pk, 'received': received}


def receive(ctx) -> Dict[str, Any]:
    return receive_receipt(ctx.obj, actor=ctx.actor, lines=(ctx.data or {}).get('lines'))


def register() -> None:
    from apps.core.services.verbs import register_command
    register_command('receipt', 'receive', receive)
