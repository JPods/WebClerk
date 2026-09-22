"""Rebuild every payable's AP ledger from its receipt (Bill: AP works just as AR does).

A receipt is the vendor's bill. Its ledger rows carry a due date from the purchase's
terms and the balance still owed, so AP has the same water level AR has.

Usage:
    python manage.py rebuild_payable_ledgers --dry-run
    python manage.py rebuild_payable_ledgers
"""
from django.core.management.base import BaseCommand

from apps.transactions.models import Purchase, Receipt


class Command(BaseCommand):
    help = "Rebuild AP ledgers from receipts and refresh vendor financials"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        from apps.accounts.services.ledger_balance import on_receipt_save, update_org_balances
        from apps.orgs.models import OrgBase
        receipts = Receipt.objects.order_by('pk')
        vendors = set()
        n = 0
        for rec in receipts:
            n += 1
            purchase = Purchase.objects.filter(pk=rec.purchase_id).only('vendor_id').first()
            if purchase and purchase.vendor_id:
                vendors.add(purchase.vendor_id)
            if not opts['dry_run']:
                on_receipt_save(rec)
        out_of_step = 0
        if not opts['dry_run']:
            for org in OrgBase.objects.filter(pk__in=vendors).only('financial'):
                update_org_balances(org)
                org.refresh_from_db()
                if not ((org.financial or {}).get('summary') or {}).get('in_step', True):
                    out_of_step += 1
                    self.stdout.write(f"  vendor {org.pk}: {(org.financial['summary'] or {}).get('mismatches')}")
        verb = 'Would rebuild' if opts['dry_run'] else 'Rebuilt'
        self.stdout.write(f"{verb} {n} payable ledger(s); {len(vendors)} vendor(s) refreshed; {out_of_step} out of step")
