"""The totals a document will have once the screen's edits are saved.

POST /wcapi/<model>/<id>/totals/ {header, lines}

The screen mirrors the server (Bill, 2026-10-25: users see changes as they make them,
without saving). It sends its unsaved header inputs and its active lines; compute_totals —
the one calculation the save runs — answers. Nothing is written. A line not yet saved is
priced under its temporary (negative) id.

    header: {finance, tax, allocations, ship_via, customer_id}   — any omitted: the stored value
    lines:  [{id, line_type, line_number, quantity, price, cost, tax}]
"""
from __future__ import annotations

from types import SimpleNamespace

from apps.core.services.door import Refused

#: Every document that carries totals. A requisition has lines but no totals; cash has neither.
TOTALS_MODELS = ('quote', 'order', 'invoice', 'purchase', 'workorder', 'receipt')

#: What compute_totals reads from a header and from each line.
HEADER_KEYS = ('finance', 'tax', 'allocations', 'ship_via', 'customer_id')
LINE_KEYS = ('line_type', 'line_number', 'quantity', 'price', 'cost', 'tax')


def totals(ctx):
    from apps.transactions.services.pricing.totals_compute import compute_totals
    record, data = ctx.obj, ctx.data
    edits = data.get('header') or {}
    lines = data.get('lines')
    if not isinstance(edits, dict) or not isinstance(lines, list):
        raise Refused(400, 'totals_needs_header_and_lines',
                      'Send {"header": {...}, "lines": [...]} — the screen\'s unsaved values.')
    header = SimpleNamespace(pk=record.pk, totals=record.totals,
                             **{k: edits.get(k, getattr(record, k, None)) for k in HEADER_KEYS})
    rows = [SimpleNamespace(pk=l.get('id'), **{k: l.get(k) for k in LINE_KEYS}) for l in lines]
    computed = compute_totals(header, rows, ctx.model_key)
    return {'totals': computed['totals'], 'line_totals': computed['line_totals']}


def register() -> None:
    from apps.core.services.verbs import register_command
    for model_key in TOTALS_MODELS:
        register_command(model_key, 'totals', totals)
