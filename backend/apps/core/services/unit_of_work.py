"""One edit, one recomputation — the unit of work.

Saving five lines of an invoice recomputes that invoice five times and saves its header
five times, so one edit bumps the header's version by five. The totals engine is not
wrong; it is being asked per row for an answer that belongs to the document
(save-path review, 2026-09-22).

WC2 had this by accident: `jAcceptButton` was the only way to save, so the work after
the branch happened once, at the end, for the record being accepted. This is the same
idea made explicit — a scope a writer opens, inside which derived work is **marked**
rather than **done**, and flushed once when the scope closes.

    with unit_of_work():
        for line in lines:
            line.save()          # marks its document dirty
        # on exit: each dirty document recomputed once, inside the same transaction

Outside a unit, nothing changes: a bare ``line.save()`` recomputes immediately, as it
always did. That keeps every caller that has not been converted working exactly as
before, and it is why this can land without touching them.
"""
from __future__ import annotations

import contextvars
import logging
from contextlib import contextmanager
from typing import Any, Callable, Dict, Tuple

logger = logging.getLogger(__name__)

# A stack, because units nest: the save door opens one, and a service it calls may open
# another. Only the outermost flushes, so the work still happens once.
_DEPTH = contextvars.ContextVar('wc_uow_depth', default=0)
_PENDING: contextvars.ContextVar[Dict[Tuple[str, Any], Callable[[], None]]] = \
    contextvars.ContextVar('wc_uow_pending', default=None)  # type: ignore[assignment]


def active() -> bool:
    return _DEPTH.get() > 0


def defer(key: Tuple[str, Any], work: Callable[[], None]) -> bool:
    """Hold this work until the unit closes. Returns False if there is no unit open, in
    which case the caller does it now.

    ``key`` is what makes it happen once: ('invoice', 41) marks that document, however
    many of its lines were saved.
    """
    if not active():
        return False
    pending = _PENDING.get()
    if pending is None:
        pending = {}
        _PENDING.set(pending)
    pending[key] = work           # last writer wins; the work re-reads from the database
    return True


@contextmanager
def unit_of_work():
    """One edit. Derived work inside is marked, and done once on the way out."""
    _DEPTH.set(_DEPTH.get() + 1)
    outermost = _DEPTH.get() == 1
    if outermost:
        _PENDING.set({})
    completed = False
    try:
        yield
        completed = True
    finally:
        _DEPTH.set(_DEPTH.get() - 1)
        if outermost:
            # A refused or failed edit is rolled back; recomputing for it is wasted work
            # that can itself fail and hide the refusal.
            if completed:
                _DEPTH.set(1)           # still inside: work marked while draining is kept
                try:
                    _drain()
                finally:
                    _DEPTH.set(0)
            _PENDING.set({})


def flush() -> None:
    """Do the marked work now, still inside the unit and its transaction.

    The verb calls this between persisting and the after hooks, so an after hook reads a
    document's current totals and ledger, not the ones from before the edit (Fable review,
    2026-09-24). Work marked after this — by an after hook — is done when the unit closes.
    """
    if not active():
        return
    _drain()


#: Derived work may mark more derived work (a recompute marks the ledger it changed).
#: Rounds are bounded: a chain this deep is a loop, and a loop fails hard.
MAX_ROUNDS = 5


def _drain() -> None:
    for _ in range(MAX_ROUNDS):
        pending = _PENDING.get() or {}
        if not pending:
            return
        _PENDING.set({})
        _flush(pending)
    raise RuntimeError(f'derived work still marking more after {MAX_ROUNDS} rounds: '
                       f'{sorted(map(str, (_PENDING.get() or {}).keys()))}')


def _flush(pending: Dict[Tuple[str, Any], Callable[[], None]]) -> None:
    """Runs inside the writer's transaction, so a failure here fails the edit.

    Fail hard (Bill, 2026-09-22): totals that silently failed to recompute are totals
    nobody can trust.
    """
    for key, work in pending.items():
        logger.debug("[UOW] recomputing %s", key)
        work()
