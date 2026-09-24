"""The documents' code hooks — what a quote, order, invoice, purchase or workorder does on
a save that other records do not.

Until 2026-09-24 this work lived in ``save_transaction_with_lines`` behind its own route,
``/wcapi/transaction/save/``. Bill ruled one door per verb: the route is deleted and its
work moves here (plan: Allie ``readmes/assessments/2026-09-24-one-route-per-verb.md`` §4).
What moved, and where:

- transfer-quantity and stock checks → ``before_save`` (ported, not dropped);
- the lines themselves → the door's line engine (``save_line_processing``);
- totals and the invoice's ledger → the door's flush — the base owns money (§5), so no
  hook posts a ledger;
- erosion detection → ``after_save``: it reads the totals the flush wrote.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from apps.core.services.behaviours import HookContext, ModelBehaviour, register
from apps.core.services.door import Refused

logger = logging.getLogger(__name__)

DOCUMENT_MODELS = ('quote', 'order', 'invoice', 'purchase', 'workorder')


def _line_qty(line_data: Dict[str, Any]) -> float:
    """The line quantity a check reads: quantity.active. No fallbacks — staged is a
    creation snapshot, placed/actioned are retired."""
    qty = line_data.get('quantity') or {}
    if not isinstance(qty, dict):
        return 0.0
    return float(qty.get('active', 0) or 0)


def check_transfer(model_key: str, parent_model: str, lines: List[Dict[str, Any]]) -> None:
    """Refuse new lines that take more than their source has left, or more stock than
    there is.

    1. Parent-child pairs only (quote→order, order→invoice; ``line_parent.PARENT_OF``):
       the quantity asked of each source line, summed, may not exceed its remaining in
       the same direction. A transfer the other way (a return, a credit) adds backlog —
       the user is in control of that (Bill, 2026-09-17). Every other conversion is
       history and consumes nothing.
    2. Invoice only: the quantity of each item may not exceed what is available (an
       order may backorder).
    """
    from apps.core.utils import registry
    from apps.transactions.services.line_parent import PARENT_OF

    parent_line = PARENT_OF.get(f'{model_key}line')
    check_remaining = bool(parent_line) and parent_line[0].lower() == f'{parent_model}line'
    check_stock = model_key == 'invoice'
    if not (check_remaining or check_stock):
        return

    SourceLine = registry.resolve(f'{parent_model}line')
    if SourceLine is None:
        raise Refused(400, 'unknown_parent_model',
                      f'This {model_key} names parent {parent_model!r}, which has no lines.',
                      {'parent_model': parent_model})

    by_source: Dict[int, float] = {}
    by_item: Dict[int, float] = {}
    for line in lines:
        if not isinstance(line, dict) or line.get('id') is not None:
            continue
        qty = _line_qty(line)
        if qty <= 0:
            continue
        source = ((line.get('refs') or {}).get('source') or {}).get(f'{parent_model}_line_id')
        if source:
            by_source[int(source)] = by_source.get(int(source), 0.0) + qty
        item = line.get('item') or {}
        item_id = item.get('id') or item.get('item_id')
        if item_id:
            by_item[int(item_id)] = by_item.get(int(item_id), 0.0) + qty

    if check_remaining and by_source:
        held = {s.pk: s for s in
                SourceLine.objects.select_for_update().filter(pk__in=list(by_source))}
        for source_id, requested in by_source.items():
            src = held.get(source_id)
            remaining = float(((src.quantity if src else None) or {}).get('remaining', 0) or 0)
            same_direction = (requested >= 0) == (remaining >= 0)
            if src is None or (same_direction and abs(requested) > abs(remaining) + 1e-9):
                raise Refused(
                    400, 'transfer_exceeds_remaining',
                    f'{parent_model} line {source_id} has {remaining:g} left; this '
                    f'{model_key} asks for {requested:g}.',
                    {'source_model': parent_model, 'source_line_id': source_id,
                     'requested': requested, 'remaining': remaining})

    if check_stock and by_item:
        from apps.products.models import Item
        items = {i.pk: i for i in Item.objects.select_for_update().filter(pk__in=list(by_item))}
        for item_id, required in by_item.items():
            item = items.get(item_id)
            qty = dict((item.quantity if item else None) or {})
            available = float(qty.get('available', qty.get('on_hand', 0)) or 0)
            if item is None or required > available + 1e-9:
                sku = (item.sku or item.ida) if item else str(item_id)
                raise Refused(
                    400, 'insufficient_inventory',
                    f'{sku} has {available:g} available; this invoice needs {required:g}.',
                    {'item_id': item_id, 'sku': sku, 'required': required,
                     'available': available})


class DocumentBehaviour(ModelBehaviour):
    """Every document: a transfer takes no more than its source has left."""

    def before_save(self, ctx: HookContext) -> None:
        lines = ctx.data.get('lines')
        parent_model = getattr(ctx.obj, 'parent_model', None)
        if lines and parent_model and getattr(ctx.obj, 'parent_id', None):
            check_transfer(ctx.model_key, str(parent_model), lines)


class OrderBehaviour(DocumentBehaviour):
    """An order records the discount it gave away."""

    def after_save(self, ctx: HookContext) -> None:
        from apps.accounts.services.value_erosion import detect_discount_erosion
        detect_discount_erosion(ctx.obj)


class InvoiceBehaviour(DocumentBehaviour):
    """An invoice records the margin it lost against its order and quote, and the
    discount it gave away. Both replace their earlier record, so a re-save is safe."""

    def after_save(self, ctx: HookContext) -> None:
        from apps.accounts.services.value_erosion import (detect_discount_erosion,
                                                          detect_margin_erosion)
        detect_margin_erosion(ctx.obj)
        detect_discount_erosion(ctx.obj)


def register_documents() -> None:
    for key in ('quote', 'purchase', 'workorder'):
        register(key, DocumentBehaviour())
    register('order', OrderBehaviour())
    register('invoice', InvoiceBehaviour())
