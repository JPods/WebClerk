"""assess_finance_charges — create this month's finance-charge invoices.

Usage:
    python manage.py assess_finance_charges --dry-run            # show who would be charged
    python manage.py assess_finance_charges                      # create, journalize, ledger them
    python manage.py assess_finance_charges --as-of 2026-09-30

Rules: company profile config.receivables (see apps/accounts/services/finance_charges.py).
"""
import json
from datetime import date

from django.core.management.base import BaseCommand

from apps.accounts.services.finance_charges import assess_finance_charges


class Command(BaseCommand):
    help = 'Assess monthly finance charges on past-due customer balances'

    def add_arguments(self, parser):
        parser.add_argument('--as-of', type=date.fromisoformat, default=None, help='Assessment date (YYYY-MM-DD, UTC)')
        parser.add_argument('--dry-run', action='store_true', help='Report charges without creating anything')

    def handle(self, *args, **options):
        result = assess_finance_charges(as_of=options['as_of'], dry_run=options['dry_run'])
        self.stdout.write(json.dumps(result, indent=2))
