"""Rebuild every invoice's AR ledger from the invoice (Bill: ledgers echo their primary records).

Before 2026-09-19 an invoice's ledger was written once, from the total at first save,
and never followed later changes; most demo invoices had none. This rebuilds each
invoice's ledger rows from invoice.totals and re-spreads received + adjusted, then
refreshes each customer's financial (including financial.summary).

Usage:
    python manage.py rebuild_invoice_ledgers --dry-run
    python manage.py rebuild_invoice_ledgers
"""
from django.core.management.base import BaseCommand

from apps.transactions.models import Invoice


class Command(BaseCommand):
    help = "Rebuild invoice AR ledgers from their invoices and refresh customer financials"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        from apps.accounts.services.ledger_balance import on_invoice_save, update_org_balances
        from apps.orgs.models import OrgBase
        invoices = Invoice.objects.order_by('pk')
        customers = set()
        n = 0
        for inv in invoices:
            n += 1
            if inv.customer_id:
                customers.add(inv.customer_id)
            if not opts['dry_run']:
                on_invoice_save(inv, replace_ledgers=True)
        for org in OrgBase.objects.filter(pk__in=customers):
            if not opts['dry_run']:
                update_org_balances(org)
        out_of_step = 0
        if not opts['dry_run']:
            for org in OrgBase.objects.filter(pk__in=customers).only('financial'):
                if not ((org.financial or {}).get('summary') or {}).get('in_step', True):
                    out_of_step += 1
                    self.stdout.write(f"  org {org.pk}: {(org.financial['summary'] or {}).get('mismatches')}")
        verb = 'Would rebuild' if opts['dry_run'] else 'Rebuilt'
        self.stdout.write(f"{verb} {n} invoice ledgers; {len(customers)} customers refreshed; {out_of_step} out of step")
