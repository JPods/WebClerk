"""A status the system moves on its own is not a person's act (2026-11-27).

Paid sets 'paid' and a reversal returns it to 'released' (totals_compute.settle_paid_status); the
one-off settle_document_statuses sets wc_demo's statuses from their facts. None of those is a person
sending an invoice, so the "invoice sent" email and Allie's order_fulfilled boundary, which fire when
an invoice moves into released, stay quiet inside ``system_status_move()``. Allie still hears the
change, as an update (Bill: "Alice can watch these changes and coach users"). No imports, so the
signals and the totals engine both read it without a cycle.
"""
from __future__ import annotations

import contextvars
from contextlib import contextmanager

_SYSTEM_MOVE: contextvars.ContextVar[bool] = contextvars.ContextVar('wc_system_status_move', default=False)


@contextmanager
def system_status_move():
    token = _SYSTEM_MOVE.set(True)
    try:
        yield
    finally:
        _SYSTEM_MOVE.reset(token)


def moved_by_system() -> bool:
    return _SYSTEM_MOVE.get()
