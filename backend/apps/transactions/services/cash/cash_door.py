"""The cash door — every change to an application is a new signed Pending.

Bill, 2026-09-22: *"If a user deletes a transaction record, it and its lines issue pending
records to account for cash and inventory changes, and it is gone."* On the cash side the
**application is the Pending**: received, paid and available are sums over applications in
state ``applied``. So nothing is ever edited back. Apply, unapply and delete each write a
new record, and the journal stays the audit trail.

What lives here:

- ``live(pending)``        what is left of an application after its reversals
- ``reverse_application`` one reversal, written and applied, or the caller fails
- ``close_queued``        an application that never applied is closed, not reversed
- the receivers that fire when a Cash, Invoice or Receipt is deleted
- the two guards that keep a cash Pending permanent and frozen once processed

Plan: ``readmes/assessments/2026-09-22-cash-door-plan.md`` (Fable-reviewed).
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.db.models import Q
from django.db.models.signals import post_delete, pre_delete, pre_save
from django.utils import timezone

logger = logging.getLogger(__name__)

AR = 'cash_application'
AP = 'cash_application_receipt'
CASH_PURPOSES = (AR, AP)


class CashDoorError(Exception):
    """A cash change the rule refuses, with coaching for the user."""


def _d(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal('0.01'))


def _target_key(purpose: str) -> str:
    return 'receipt_id' if purpose == AP else 'invoice_id'


def _pending_model():
    from apps.core.models.pending import Pending
    return Pending


# ── what is left of an application ────────────────────────────────────

def live(pending) -> Decimal:
    """The application's amount, less every applied reversal of it.

    An application that was never applied is worth nothing: no money moved, so there is
    nothing to reverse (it is closed instead — ``close_queued``).
    """
    changes = pending.changes if isinstance(pending.changes, dict) else {}
    if changes.get('state') != 'applied':
        return Decimal('0.00')
    amount = _d(changes.get('amount'))
    reversed_sum = Decimal('0.00')
    for p in (_pending_model().objects
              .filter(purpose=pending.purpose, changes__reverses=pending.pk,
                      changes__state='applied')
              .only('changes')):
        reversed_sum += _d((p.changes or {}).get('amount'))
    return amount + reversed_sum


def _applications(*, cash_id: Optional[int] = None, target_id: Optional[int] = None,
                  purpose: Optional[str] = None, state: Optional[str] = None) -> List[Any]:
    """Applications matching the filter, oldest first. Reversals are excluded: a reversal
    is not itself reversed, it is what a reversal produces."""
    qs = _pending_model().objects.filter(purpose__in=CASH_PURPOSES)
    if purpose:
        qs = qs.filter(purpose=purpose)
    if cash_id is not None:
        qs = qs.filter(changes__cash_id=cash_id)
    if target_id is not None:
        qs = qs.filter(Q(changes__invoice_id=target_id) | Q(changes__receipt_id=target_id))
    if state:
        qs = qs.filter(changes__state=state)
    return [p for p in qs.order_by('dt_created')
            if not (p.changes or {}).get('reverses')]


# ── the two ways an application stops counting ────────────────────────

def reverse_application(pending, reason: str, *, acted_by: Optional[int] = None,
                        amount: Optional[Decimal] = None, skip_refresh: tuple = (),
                        gateway_event_id: Optional[str] = None) -> Optional[Any]:
    """Write one reversing Pending and apply it. Returns the reversal, or None if there
    was nothing left to reverse.

    A reversal is judged against the **live amount of the application it reverses**, never
    against the document: its sign always runs against the document, which is exactly what
    ``_check_application`` refuses. It carries the reversed application's ``kind`` so an
    adjustment stays an adjustment in ``_applied_split``, plus ``reverses``, which is what
    makes it a reversal.

    Idempotent by design (Fable): Django sends every ``pre_delete`` before deleting any
    row, so deleting an invoice can reach the same application twice. Nothing left to
    reverse is a no-op, not an error.
    """
    from apps.transactions.models import Cash, Invoice, Receipt

    changes = pending.changes if isinstance(pending.changes, dict) else {}
    remaining = live(pending)
    if remaining == 0:
        return None
    amount = -remaining if amount is None else _d(amount)

    key = _target_key(pending.purpose)
    target_id = changes.get(key)
    cash_id = changes.get('cash_id')

    # Blocking locks, in one order everywhere: cash, then document. The reversal must land
    # inside this transaction — a queued reversal of a record about to be deleted would
    # never apply (Fable).
    cash = Cash.objects.select_for_update().filter(pk=cash_id).first()
    model = Receipt if pending.purpose == AP else Invoice
    target = model.objects.select_for_update().filter(pk=target_id).first()

    reversal = _pending_model().objects.create(
        model_name='cash',
        record_id=str(cash_id),
        name=f'Reversal of application #{pending.pk} ({amount})',
        purpose=pending.purpose,
        changes={
            'cash_id': cash_id,
            key: target_id,
            'amount': float(amount),
            'reason': reason,
            'acted_by': acted_by,
            'kind': changes.get('kind') or 'cash_application',
            'reverses': pending.pk,
            'state': 'pending',
            'dt_applied': None,
            **({'gateway_event_id': gateway_event_id} if gateway_event_id else {}),
        },
    )
    reversal.refresh_from_db()
    if not reversal.is_processed():
        raise CashDoorError(
            f"the reversal of application {pending.pk} could not be applied, so nothing was "
            f"changed. The cash or the document is locked by another write; try again.")

    _refresh_after(cash if 'cash' not in skip_refresh else None,
                   target if 'target' not in skip_refresh else None)
    logger.info("Reversed application %s by %s (%s)", pending.pk, amount, reason)
    return reversal


def relink_deposits(order, invoice) -> int:
    """A deposit taken on an order follows the order to its invoice (the convert base calls
    this). Only a deposit not yet linked to an invoice moves: a second partial invoice from
    the same order no longer takes the first one's deposit. No money moves — the Cash is
    re-pointed and stays available for a person to apply (Bill, 2026-09-17)."""
    from apps.transactions.models import Cash
    moved = 0
    for cash in Cash.objects.select_for_update().filter(
            is_active=True, parent_model='order', parent_id=order.pk, invoice__isnull=True):
        cash.invoice_id = invoice.pk
        refs = cash.refs if isinstance(cash.refs, dict) else {}
        ids = list(refs.get('invoice_ids') or [])
        if invoice.pk not in ids:
            refs['invoice_ids'] = ids + [invoice.pk]
        cash.refs = refs
        cash.save(update_fields=['invoice_id', 'refs', 'dt_modified', 'version'])
        moved += 1
    return moved


def close_queued(pending, reason: str, *, acted_by: Optional[int] = None) -> bool:
    """Close an application that never applied. No money moved, so there is nothing to
    reverse: it is marked canceled and processed, with the reason. This is the one
    in-place close, and only ever on an unprocessed Pending."""
    changes = dict(pending.changes or {})
    if changes.get('state') == 'applied' or pending.is_processed():
        raise CashDoorError(
            f"application {pending.pk} has already applied: unapply it, which writes a "
            f"reversing record. A processed record is never edited.")
    if changes.get('state') == 'canceled':
        return False
    changes['state'] = 'canceled'
    changes['dt_canceled'] = timezone.now().isoformat()
    changes['cancel_reason'] = reason
    changes['acted_by'] = acted_by
    pending.changes = changes
    pending.dt_processed = int(timezone.now().timestamp() * 1000)
    pending.save(update_fields=['changes', 'dt_processed', 'dt_modified', 'version'])
    from apps.transactions.services.cash.cash_pending import note_application
    note_application(pending, 'closed')
    from apps.core.services.balance_checker import log_balance_event
    log_balance_event(pending, True, event='cancel')
    return True


def _refresh_after(cash=None, target=None) -> None:
    """Recompute what the change moved. The record being deleted is passed as None."""
    from apps.transactions.services.cash.cash_pending import (
        refresh_cash_available, refresh_invoice_cash)
    from apps.transactions.services.cash.cash_pending_receipt import refresh_receipt_paid

    if target is not None:
        if target._meta.model_name == 'receipt':
            refresh_receipt_paid(target)
            _refresh_receipt_status(target)
        else:
            refresh_invoice_cash(target)
    if cash is not None:
        refresh_cash_available(cash)


def _refresh_receipt_status(receipt) -> None:
    """A payable's status is derived both ways. It used to move only toward paid, so a
    reversed receipt stayed 'paid' with nothing paid on it (Fable)."""
    from apps.transactions.services.cash.cash_pending_receipt import _applied
    paid = _applied(receipt_id=receipt.pk)
    balance = _d((receipt.totals or {}).get('total')) - paid
    status = 'paid' if (paid and balance <= 0) else ('partially_paid' if paid else 'open')
    if receipt.status != status:
        receipt.status = status
        receipt.save(update_fields=['status', 'dt_modified', 'version'])


# ── deleting a record reverses its cash ───────────────────────────────

def _unwind(*, cash=None, target=None, reason: str) -> Dict[str, int]:
    """Every live application of the record being deleted is reversed; every queued one is
    closed. The record itself is not refreshed — it is about to be gone."""
    kwargs = {'cash_id': cash.pk} if cash is not None else {'target_id': target.pk}
    skip = ('cash',) if cash is not None else ('target',)
    reversed_count = closed = 0
    for application in _applications(state='applied', **kwargs):
        if reverse_application(application, reason, skip_refresh=skip) is not None:
            reversed_count += 1
    for application in _applications(state='pending', **kwargs):
        if not application.is_processed() and close_queued(application, reason):
            closed += 1
    return {'reversed': reversed_count, 'closed': closed}


def _on_cash_delete(sender, instance, **kwargs):
    """Deleting a cash returns what it had applied: each live application is reversed, so
    the invoice or receipt it settled opens again."""
    result = _unwind(cash=instance, reason=f'cash {instance.pk} deleted')
    logger.info("Cash %s deleted: %s applications reversed, %s queued closed",
                instance.pk, result['reversed'], result['closed'])


def _refuse_if_paid(instance, kind: str) -> None:
    """A document with money against it is not deleted out from under it.

    Bill, 2026-09-22: *"I would much prefer users have to purposefully delete dependent
    records than to risk deleting a parent whose children should remain."* The money is
    the user's to deal with: unapply it, then delete. Detaching silently would leave the
    payment pointing at nothing, which is the same quiet loss in a different shape.
    """
    live_applications = [(p, live(p)) for p in _applications(target_id=instance.pk,
                                                             state='applied')]
    owed = [f"application #{p.pk} ({amount} from cash {(p.changes or {}).get('cash_id')})"
            for p, amount in live_applications if amount != 0]
    if owed:
        raise CashDoorError(
            f"{kind} {instance.pk} still has money applied to it: {'; '.join(owed)}. "
            f"Unapply the payment first, then delete the {kind}. Unapplying writes a "
            f"reversing record, so the money returns to the cash and the trail stays.")


def _refuse_if_cash_points_here(instance, kind: str) -> None:
    """A cash record naming this document keeps it alive too. The column is SET_NULL so
    the money survives a delete that gets this far, but the user is told first."""
    from apps.transactions.models import Cash

    field = {'invoice': 'invoice_id', 'receipt': 'receipt_id', 'purchase': 'purchase_id'}[kind]
    rows = list(Cash.objects.filter(**{field: instance.pk}).values_list('pk', flat=True)[:10])
    if rows:
        listed = ', '.join(f'#{pk}' for pk in rows)
        raise CashDoorError(
            f"cash {listed} {'points' if len(rows) == 1 else 'point'} at {kind} "
            f"{instance.pk}. Deal with the cash first — unapply and delete it, or point it "
            f"elsewhere — then delete the {kind}.")


def _on_document_delete(sender, instance, **kwargs):
    """An invoice or receipt with money against it refuses to be deleted (Bill, 2026-09-22).
    With nothing applied, its queued applications are closed and it goes."""
    kind = sender._meta.model_name
    _refuse_if_paid(instance, kind)
    _refuse_if_cash_points_here(instance, kind)
    result = _unwind(target=instance, reason=f'{kind} {instance.pk} deleted')
    logger.info("%s %s deleted: %s applications reversed, %s queued closed",
                kind, instance.pk, result['reversed'], result['closed'])


def _on_purchase_delete(sender, instance, **kwargs):
    """A purchase with a payment against it refuses too — AR and AP are symmetric
    (Bill: "same with purchases"). A purchase carries no applications of its own; the
    cash record names it."""
    _refuse_if_cash_points_here(instance, 'purchase')


def _on_record_deleted(sender, instance, **kwargs):
    """Ledger rows point at their record by ``parent_id`` with no FK, so a delete leaves
    them behind, still feeding aging and the org balances (wc_demo holds 37 such orphans).
    They go with the record, and the party's balances are recomputed."""
    from apps.accounts.models import Ledger
    from apps.accounts.services.ledger_balance import update_org_balances
    from apps.orgs.models import OrgBase

    model_name = sender._meta.model_name
    Ledger.objects.filter(model_name=model_name, parent_id=instance.pk).delete()
    for attr in ('customer_id', 'vendor_id'):
        org_id = getattr(instance, attr, None)
        org = OrgBase.objects.filter(pk=org_id).first() if org_id else None
        if org is not None:
            # Fail hard (Bill, 2026-09-22): balances that silently failed to recompute are
            # balances nobody can trust. The delete fails with them.
            update_org_balances(org)


# ── a cash Pending is permanent, and frozen once processed ────────────

#: Data-set kinds whose journal a repair may rewrite (Bill, 2026-09-26: demo, training and
#: dev only; a live company's journal is never deleted). ``DATA_SET_KIND`` defaults to live:
#: install.sh writes DATA_SET_ID=DEV on every install, so the id cannot be the test.
DISPOSABLE_DATA_SETS = ('demo', 'training', 'dev')
_orphan_delete_ok: set = set()


def data_set_is_disposable() -> bool:
    from decouple import config
    return config('DATA_SET_KIND', default='live').strip().lower() in DISPOSABLE_DATA_SETS


def delete_orphan_application(pending_id: int, reason: str) -> Dict[str, Any]:
    """Delete one cash application whose cash and document are both gone — the only way a
    cash Pending is ever deleted, and only on a demo, training or dev data set (Bill,
    2026-09-26: a raw purge left six on wc_demo; unapplying needs the cash and the document).
    Logged with what it said. Refused for anything else: the journal is permanent."""
    from apps.transactions.models import Cash, Invoice, Receipt
    if not data_set_is_disposable():
        raise CashDoorError('a cash application is deleted only on a demo, training or dev data '
                            'set (DATA_SET_KIND); this one is live. Unapply it instead.')
    p = _pending_model().objects.get(pk=pending_id, purpose__in=CASH_PURPOSES)
    c = p.changes or {}
    doc_model, doc_key = (Receipt, 'receipt_id') if p.purpose == AP else (Invoice, 'invoice_id')
    cash_gone = c.get('cash_id') is not None and not Cash.objects.filter(pk=c['cash_id']).exists()
    doc_gone = c.get(doc_key) is not None and not doc_model.objects.filter(pk=c[doc_key]).exists()
    if not (cash_gone and doc_gone):
        raise CashDoorError(f'pending {pending_id} still points at a live cash or document; '
                            f'unapply it instead.')
    logger.warning("[cash_door] deleting orphan application pending %s (%s): %s", pending_id,
                   reason, c)
    _orphan_delete_ok.add(p.pk)
    try:
        p.delete()
    finally:
        _orphan_delete_ok.discard(pending_id)
    return {'deleted': pending_id, 'changes': c, 'reason': reason}


def _on_pending_delete(sender, instance, **kwargs):
    """Pendings are permanent (Bill, 2026-09-21). wcapi can reach a Pending directly
    through the record registry; this is where that stops. The one exception is
    ``delete_orphan_application`` on a disposable data set."""
    if instance.pk in _orphan_delete_ok:
        return
    if instance.purpose in CASH_PURPOSES:
        raise CashDoorError(
            f"a cash application (pending {instance.pk}) is permanent: it is the record the "
            f"balances are computed from. To undo it, unapply it — that writes a reversing "
            f"record and leaves the trail intact.")


def _on_pending_save(sender, instance, **kwargs):
    """Once an application has applied, what it says is what happened. The applier writes
    ``changes`` and ``dt_processed`` in the same save, so the freeze compares the row in
    the database, not the instance (Fable)."""
    if instance.purpose not in CASH_PURPOSES or not instance.pk:
        return
    old = (_pending_model().objects.filter(pk=instance.pk)
           .values('dt_processed', 'changes').first())
    if not old or not old['dt_processed']:
        return
    if (old['changes'] or {}) != (instance.changes or {}):
        raise CashDoorError(
            f"application {instance.pk} has already applied and cannot be edited. "
            f"Correct it with a new record: unapply it, or record another application.")


def connect() -> None:
    """Wire the door. Called from the transactions app config."""
    from apps.core.models.pending import Pending
    from apps.transactions.models import Cash, Invoice, Purchase, Receipt

    pre_delete.connect(_on_cash_delete, sender=Cash, dispatch_uid='cash_door.cash')
    pre_delete.connect(_on_document_delete, sender=Invoice, dispatch_uid='cash_door.invoice')
    pre_delete.connect(_on_document_delete, sender=Receipt, dispatch_uid='cash_door.receipt')
    pre_delete.connect(_on_purchase_delete, sender=Purchase, dispatch_uid='cash_door.purchase')
    for model in (Cash, Invoice, Receipt):
        post_delete.connect(_on_record_deleted, sender=model,
                            dispatch_uid=f'cash_door.ledgers.{model._meta.model_name}')
    pre_delete.connect(_on_pending_delete, sender=Pending, dispatch_uid='cash_door.pending_delete')
    pre_save.connect(_on_pending_save, sender=Pending, dispatch_uid='cash_door.pending_save')


__all__ = ['live', 'reverse_application', 'close_queued', 'CashDoorError', 'connect',
           'AR', 'AP', 'CASH_PURPOSES']
