"""An AP application carries the **document's** sign, and cash available is refreshed.

    manage.py fix_ap_application_signs            # show what would change
    manage.py fix_ap_application_signs --apply

The convention, which the AP path has had from the start:

    receipt total  = +100.00   what we owe the vendor
    cash amount    =  -60.00   money leaving
    application    = +60.00    how much of that payment went to this bill
    → receipt.totals['paid'] = 60.00, balance = 40.00

``paid`` and ``balance`` are derived from the applications, so an application stored with
the cash's sign instead of the document's makes a receipt report a negative amount paid.

What was actually broken was never the applications: ``refresh_cash_available`` computed
``amount − Σ applied`` on both sides, and on AP the two point in opposite directions, so
-60.00 paid out of a -60.00 payment reported -120.00 still available. Every AP payment drove
the figure away from zero and the vendor summary inflated with it. One operator, now fixed
in ``cash_pending_receipt.refresh_cash_available``.

This command puts any row that disagrees with the document back into the document's
convention, and refreshes ``available`` on every cash carrying an AP application — it is a
stored column, so it does not correct itself on read.

Safe to run twice: a row that already agrees is left alone.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models.pending import Pending
from apps.transactions.models import Cash, Receipt
from apps.transactions.services.cash.cash_pending_receipt import RECEIPT_CASH_PURPOSE


def _sign(value) -> int:
    return (value > 0) - (value < 0)


class Command(BaseCommand):
    help = "Align AP cash applications with their receipt's sign, and refresh cash available."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='write the changes (default: show them only)')

    def handle(self, *args, **options):
        apply_changes = options['apply']

        rows = list(Pending.objects.filter(purpose=RECEIPT_CASH_PURPOSE).order_by('pk'))
        receipt_signs = {
            r.pk: _sign(Decimal(str((r.totals or {}).get('total') or 0)))
            for r in Receipt.objects.only('pk', 'totals')
        }

        to_fix, skipped = [], 0
        for pending in rows:
            changes = pending.changes if isinstance(pending.changes, dict) else {}
            amount = Decimal(str(changes.get('amount') or 0))
            doc_sign = receipt_signs.get(changes.get('receipt_id'))
            if not amount or not doc_sign:
                skipped += 1
                continue
            if _sign(amount) == doc_sign:
                continue                          # already agrees — idempotent
            to_fix.append((pending, changes, amount, -amount))

        if to_fix:
            for pending, _changes, before, after in to_fix:
                self.stdout.write(f"  pending {pending.pk}: {before} → {after}")
        else:
            self.stdout.write(
                f"{len(rows)} AP applications, all already signed like their receipt."
                + (f" ({skipped} without an amount or a receipt)" if skipped else ""))

        if not apply_changes:
            self.stdout.write(self.style.WARNING(
                f"{len(to_fix)} of {len(rows)} would change; cash available would be "
                f"refreshed either way. Re-run with --apply."))
            return

        touched_cash = set()
        with transaction.atomic():
            for pending, changes, _before, after in to_fix:
                changes['amount'] = float(after)
                pending.changes = changes
                pending.save(update_fields=['changes', 'dt_modified', 'version'])

        for pending in rows:
            changes = pending.changes if isinstance(pending.changes, dict) else {}
            if changes.get('cash_id'):
                touched_cash.add(changes['cash_id'])

        from apps.transactions.services.cash.cash_pending_receipt import (
            refresh_cash_available, refresh_receipt_paid)

        refreshed = 0
        for cash in Cash.objects.filter(pk__in={c for c in touched_cash if c}):
            before = cash.available
            refresh_cash_available(cash)
            if cash.available != before:
                self.stdout.write(f"  cash {cash.pk}: available {before} → {cash.available}")
            refreshed += 1

        # paid and balance are derived from the applications too, so a re-signed row
        # leaves them stale in the same way.
        receipts = {(p.changes or {}).get('receipt_id') for p in rows}
        for receipt in Receipt.objects.filter(pk__in={r for r in receipts if r}):
            refresh_receipt_paid(receipt)

        self.stdout.write(self.style.SUCCESS(
            f"{len(to_fix)} AP applications re-signed, {refreshed} cash refreshed, "
            f"{len([r for r in receipts if r])} receipts recomputed."))
