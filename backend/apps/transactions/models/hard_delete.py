"""Transactions are deleted outright, never soft (Bill, 2026-09-22).

"Apply the same rule of no soft delete to all transactions; their lines and line behaviors
get too messy. If a user deletes a transaction record, it and its lines issue pending records
to account for cash and inventory changes, and it is gone. If the user needs to recreate the
transaction, they do from scratch." And: "Once a document has been journalized it cannot be
deleted, or have values edited within our scope of work."

No model has a deleted flag any more (Bill, 2026-09-22: soft delete removed everywhere), so what is
left to guard is the posted record. Every transaction header, every line and every Cash:
  - refuses deletion once journalized (is_locked / dt_journaled) or reconciled (Cash);
  - a line refuses to be added to, or deleted from, a journalized document.
The delete guard is a pre_delete receiver, so it also stops queryset deletes and a header's
CASCADE, which never call Model.delete().
~/Allie/readmes/assessments/2026-09-22-one-door-line-pendings.md §8-9
"""
from __future__ import annotations

from django.db.models.signals import pre_delete


class JournalizedDeleteRefused(ValueError):
    def __init__(self, record, why):
        super().__init__(
            f"{_label(record)} is {why} and cannot be deleted or changed. Correct it with a new "
            f"record: a credit memo, or a reversing cash.")


def _label(record) -> str:
    return f"{record._meta.verbose_name} {getattr(record, 'ida', '') or record.pk}"


def _posted(record) -> str | None:
    """Why this record is closed to deletion, or None."""
    if getattr(record, 'is_locked', False) or getattr(record, 'dt_journaled', 0):
        return 'journalized'
    if getattr(record, 'reconciled', False):
        return 'reconciled'
    return None


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
            if why:
                raise JournalizedDeleteRefused(header, why)
        return super().save(*args, **kwargs)


def refuse_posted_delete(sender, instance, **kwargs):
    if not isinstance(instance, HardDeleteOnly):
        return
    for record in (instance, instance._header_for_guard()):
        why = _posted(record)
        if why:
            raise JournalizedDeleteRefused(record, why)


def connect():
    pre_delete.connect(refuse_posted_delete, dispatch_uid='transactions.hard_delete.refuse_posted')
