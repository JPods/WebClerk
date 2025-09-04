"""Management command to seed Orders with child OrderLine rows.

Usage examples:
  python manage.py seed_transactions --orders 3 --min-lines 2 --max-lines 5
  python manage.py seed_transactions --orders 2 --force

Requirements:
  - At least one CustomerOrg and VendorOrg (unless --force supplied)
  - Order and OrderLine models (line_variants)

Creates:
  N Order records each with a random number (min-lines..max-lines) of OrderLine
  JSON fields on lines are initialized via ensure_json_defaults then mutated.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
import random
from decimal import Decimal

from apps.orgs.models import CustomerOrg, VendorOrg
from apps.transactions.models.line_variants import SalesOrder, SalesOrderLine


class Command(BaseCommand):
    help = "Seed Orders with associated OrderLine rows (customer/vendor linkage)."

    def add_arguments(self, parser):  # pragma: no cover - simple CLI wiring
        parser.add_argument('--orders', type=int, default=3, help='Number of orders to create (default 3).')
        parser.add_argument('--min-lines', type=int, default=2, help='Minimum lines per order (default 2).')
        parser.add_argument('--max-lines', type=int, default=5, help='Maximum lines per order (default 5).')
        parser.add_argument('--force', action='store_true', help='Proceed even if no customers/vendors present.')

    def handle(self, *args, **opts):  # noqa: D401
        orders_requested = max(1, opts['orders'])
        min_lines = max(1, opts['min_lines'])
        max_lines = max(min_lines, opts['max_lines'])
        force = opts['force']

        customers = list(CustomerOrg.objects.all()[:50])
        vendors = list(VendorOrg.objects.all()[:50])
        if (not customers or not vendors) and not force:
            self.stdout.write(self.style.ERROR('Need at least one customer and one vendor (or use --force).'))
            return

        created_orders = 0
        created_lines = 0

        with transaction.atomic():
            for n in range(orders_requested):
                order_no = f"SO-{random.randint(100000, 999999)}"
                order = SalesOrder.objects.create(order_no=order_no)
                created_orders += 1
                line_total = random.randint(min_lines, max_lines)
                for i in range(line_total):
                    line = SalesOrderLine.objects.create(
                        parent=order,
                        parent_ref_id=order.pk,  # use pk to avoid accessing a non-existent 'id' attribute
                        status='open',
                        type_sale='standard',
                        probability=None,
                    )
                    # Initialize JSON structures
                    line.ensure_json_defaults()
                    # Mutate safely
                    if isinstance(line.item, dict):
                        line.item['description'] = f"Seed Item {n+1}-{i+1}"
                        line.item['line_number'] = i + 1
                    if isinstance(line.source, dict):
                        if customers:
                            line.source.setdefault('customer_id', getattr(random.choice(customers), 'id', 0))
                        if vendors:
                            line.source.setdefault('vendor_id', getattr(random.choice(vendors), 'id', 0))
                    if isinstance(line.price, dict):
                        unit_price = Decimal(random.randint(10, 200))
                        line.price['unit'] = float(unit_price)
                    if isinstance(line.cost, dict):
                        line.cost['unit'] = float(line.price.get('unit', 0) * 0.6 if isinstance(line.price, dict) else 0)
                    if isinstance(line.quantity, dict):
                        line.quantity.setdefault('placed', 1)
                    # Persist mutated JSON blobs
                    line.save(update_fields=['item', 'source', 'price', 'cost', 'quantity', 'status', 'type_sale'])
                    created_lines += 1

        self.stdout.write(self.style.SUCCESS(
            f"Created {created_orders} orders and {created_lines} order lines (range {min_lines}-{max_lines} lines/order)."
        ))
