"""Overpayment belongs to the customer, not to an invoice (Bill, 2026-09-19).

An invoice with a negative balance means more cash was applied to it than it asked
for. In the real world that surplus is the customer's money on account: unapplied
cash, visible as a cash ledger row, spendable on the next invoice or refundable.
Hidden inside an invoice it shows nowhere and the ledger echo cannot match
(the AR row cannot go negative once the invoice is settled).

This walks each overpaid invoice's applications, newest first, and moves the surplus
back to the cash record by unapplying and re-applying the smaller amount, so both
steps stay in the audit trail. Saving the cash rebuilds its ledger row, so the money
appears in the ledger; the invoice and the customer are then refreshed.

Usage:
    python manage.py fix_overpaid_invoices --dry-run
    python manage.py fix_overpaid_invoices
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.core.models.pending import Pending
from apps.transactions.models import Cash, Invoice
from apps.transactions.services.cash.cash_pending import (
    CASH_PURPOSE, apply_cash_to_invoice, refresh_invoice_cash, unapply_cash_application,
)


def _d(v) -> Decimal:
    return Decimal(str(v or 0))


class Command(BaseCommand):
    help = "Move invoice overpayments back to unapplied cash, visible in the ledger"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        moved = 0
        for inv in Invoice.objects.order_by('pk'):
            totals = inv.totals or {}
            balance, total = _d(totals.get('balance')), _d(totals.get('total'))
            # A credit memo (negative total) is meant to have a negative balance: it is
            # what we owe the customer. Only a positive invoice paid past zero is overpaid.
            if balance >= 0 or total <= 0:
                continue
            surplus = -balance
            self.stdout.write(f"{inv.ida or inv.pk}: balance {balance}, moving {surplus} to unapplied cash")
            applications = [
                p for p in Pending.objects.filter(
                    purpose=CASH_PURPOSE, changes__invoice_id=inv.pk, changes__state='applied'
                ).order_by('-pk')
            ]
            for pending in applications:
                if surplus <= 0:
                    break
                applied = _d((pending.changes or {}).get('amount'))
                cash_id = (pending.changes or {}).get('cash_id')
                take = min(applied, surplus)
                keep = applied - take
                self.stdout.write(
                    f"  application {pending.pk}: cash {cash_id} applied {applied} → keep {keep}, "
                    f"{take} back to the customer's account")
                if not dry:
                    unapply_cash_application(pending.pk, reason='Overpayment moved to unapplied cash')
                    if keep > 0:
                        apply_cash_to_invoice(cash_id, inv.pk, keep, reason='Re-applied without the overpayment')
                surplus -= take
                moved += 1
            if not dry:
                inv.refresh_from_db()
                refresh_invoice_cash(inv)
                for cash in Cash.objects.filter(pk__in=[(p.changes or {}).get('cash_id') for p in applications]):
                    cash.save()          # rebuilds the cash ledger row from available
                self.stdout.write(f"  {inv.ida or inv.pk}: balance now {(inv.totals or {}).get('balance')}")
        verb = 'Would move' if dry else 'Moved'
        self.stdout.write(self.style.SUCCESS(f"{verb} {moved} application(s) back to unapplied cash"))
