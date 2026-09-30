"""Transactions are deleted outright, never soft (Bill, 2026-09-22).

"Apply the same rule of no soft delete to all transactions; their lines and line behaviors
get too messy. If a user deletes a transaction record, it and its lines issue pending records
to account for cash and inventory changes, and it is gone. If the user needs to recreate the
transaction, they do from scratch." And: "Once a document has been journalized it cannot be
deleted, or have values edited within our scope of work."

No model has a deleted flag any more (Bill, 2026-09-22: soft delete removed everywhere), so what is
left to guard is the posted record. Every transaction header, every line and every Cash:
  - refuses deletion once journalized (dt_journaled), reconciled (Cash) or received (a receipt
    line with goods on the shelf, and its receipt: Bill, 2026-09-30);
  - a line refuses to be added to, or deleted from, a journalized document.
The delete guard is a pre_delete receiver, so it also stops queryset deletes and a header's
CASCADE, which never call Model.delete().
~/Allie/readmes/assessments/2026-09-22-one-door-line-pendings.md §8-9
"""
from __future__ import annotations

from django.db.models.signals import pre_delete


class JournalizedDeleteRefused(ValueError):
    def __init__(self, record, why):
        remedy = ("a count workorder: its goods are in layers, and a layer never changes"
                  if why == 'received' else "a new record: a credit memo, or a reversing cash")
        super().__init__(f"{_label(record)} is {why} and cannot be deleted or changed. "
                         f"Correct it with {remedy}.")


def _label(record) -> str:
    return f"{record._meta.verbose_name} {getattr(record, 'ida', '') or record.pk}"


def _posted(record) -> str | None:
    """Why this record is closed to deletion, or None."""
    if getattr(record, 'dt_journaled', 0):
        return 'journalized'
    if getattr(record, 'reconciled', False):
        return 'reconciled'
    if _received(record):
        return 'received'
    return None


def _received(record) -> bool:
    """A receipt line that has received goods, or a receipt with one (Bill, 2026-09-28/30: its
    layers never change, so the line cannot be taken back by deleting it)."""
    name = record._meta.model_name
    if name == 'receiptline':
        return float((record.quantity or {}).get('active') or 0) > 0
    if name == 'receipt' and record.pk:
        from apps.transactions.models import ReceiptLine
        return ReceiptLine.objects.filter(receipt_id=record.pk, quantity__active__gt=0).exists()
    return False


class HardDeleteOnly:
    """Mixin for transaction headers, lines and Cash. Place before BaseModel."""

    def _header_for_guard(self):
        """A line's document; a header is its own.

        No try/except: a line whose parent cannot be read is a fault, and a swallowed
        fault here would let a journalized document be deleted (Bill, 2026-09-22:
        "failing hard will make seeing the failure more clear").
        """
        return self.parent if hasattr(self, 'parent_line_id') else self

    def delete(self, *args, **kwargs):
        refuse_posted_delete(type(self), self)    # before Django opens its delete transaction
        return super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        if self._state.adding and hasattr(self, 'parent_line_id'):
            header = self._header_for_guard()
            why = _posted(header)
            if why and why != 'received':    # a partly received receipt still takes planned lines
                raise JournalizedDeleteRefused(header, why)
        return super().save(*args, **kwargs)


def refuse_posted_delete(sender, instance, **kwargs):
    if not isinstance(instance, HardDeleteOnly):
        return
    header = instance._header_for_guard()
    for record in (instance, header):
        why = _posted(record)
        if why == 'received' and record is header and header is not instance:
            continue    # a line not yet received may leave a partly received receipt
        if why:
            raise JournalizedDeleteRefused(record, why)


def connect():
    pre_delete.connect(refuse_posted_delete, dispatch_uid='transactions.hard_delete.refuse_posted')
