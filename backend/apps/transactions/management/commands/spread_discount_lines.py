"""Spread existing document discount lines into line discounts (Bill, 2026-09-19).

Before the line model, a discount line on a quote, order or invoice was its own
calculation, and the old converter turned some of them into +$ product lines.
This repairs both, once:

  1. A child line whose parent line is a discount line, but which was saved as a
     product (the conversion defect fixed in 780b352), is set back to discount.
  2. Every discount line with an amount (settlement/cash discounts excepted) is
     spread into its document's product lines and kept at zero as the record.

Usage:
    python manage.py spread_discount_lines --dry-run
    python manage.py spread_discount_lines
Then: python manage.py backfill_totals --all   (recompute every document under the engine)
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.transactions.models import InvoiceLine, OrderLine, QuoteLine
from apps.transactions.services.line_parent import PARENT_OF
from apps.transactions.services.pricing.document_discount import spread_discount_line


class Command(BaseCommand):
    help = 'Spread document discount lines into line discounts; repair discount lines converted as products'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        from django.apps import apps as dj_apps

        # 1. Children converted as products from a discount parent.
        repaired = []
        for Child in (OrderLine, InvoiceLine):
            parent_name = PARENT_OF[Child._meta.model_name][0]
            Parent = dj_apps.get_model('transactions', parent_name)
            discount_parents = set(Parent.objects.filter(line_type='discount').values_list('pk', flat=True))
            for child in Child.objects.filter(parent_line_id__in=discount_parents).exclude(line_type='discount'):
                repaired.append((Child.__name__, child.pk, child.line_type))
                if not dry:
                    child.line_type = 'discount'
                    child.save(update_fields=['line_type'])

        # 2. Spread every discount line that still carries an amount.
        spread = []
        for Line in (QuoteLine, OrderLine, InvoiceLine):
            for line in Line.objects.filter(line_type='discount').exclude(purpose='cash_discount').order_by('pk'):
                q = Decimal(str((line.quantity or {}).get('active') or 1))
                amount = abs(q * Decimal(str((line.price or {}).get('unit') or 0)))
                if amount == 0:
                    continue
                spread.append((Line.__name__, line.pk, float(amount)))
                if not dry:
                    with transaction.atomic():
                        try:
                            spread_discount_line(line)
                        except ValueError as exc:
                            self.stdout.write(self.style.WARNING(f'  {Line.__name__} {line.pk}: not spread — {exc}'))

        verb = 'Would' if dry else 'Did'
        self.stdout.write(f'{verb} set back to discount: {len(repaired)} line(s) {repaired}')
        self.stdout.write(f'{verb} spread: {len(spread)} discount line(s) {spread}')
        if not dry:
            self.stdout.write('Now run: python manage.py backfill_totals --all')
