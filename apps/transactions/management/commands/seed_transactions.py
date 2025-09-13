from django.core.management.base import BaseCommand
from django.db import transaction
from typing import Optional
import random

from apps.core.models import Contact
from apps.products.models import Item
from apps.transactions.models.line_variants import SalesOrder, SalesOrderLine


class Command(BaseCommand):
    help = "Seed sample SalesOrders with SalesOrderLines for demo/testing"

    def add_arguments(self, parser):
        parser.add_argument('--orders', type=int, default=2, help='Number of sales orders to create')
        parser.add_argument('--lines', type=int, default=3, help='Lines per order')

    def handle(self, *args, **options):
        orders = int(options.get('orders') or 2)
        lines_per = int(options.get('lines') or 3)

        created_orders = 0
        created_lines = 0

        # Try to find an existing contact to link
        contact: Optional[Contact] = Contact.objects.order_by('id').first()

        # Fetch items to use on lines; fall back to creating placeholder items if none
        items = list(Item.objects.all()[:10])
        if not items:
            # Create a couple of placeholder items
            for i in range(3):
                itm = Item.objects.create(
                    ida=f"DEMO-ITEM-{i+1}",
                )
                items.append(itm)

        with transaction.atomic():
            for oi in range(orders):
                order = SalesOrder.objects.create(order_no=f"SO-DEMO-{SalesOrder.objects.count()+1:04d}")

                # Link related via refs.links so related endpoint can forward-hydrate
                refs = order.refs or {}
                links = refs.get('links') or {}
                if contact:
                    links.setdefault('contacts', [])
                    if contact.id not in links['contacts']:
                        links['contacts'].append(contact.id)
                refs['links'] = links
                order.refs = refs
                order.save(update_fields=['refs'])

                created_orders += 1

                for li in range(lines_per):
                    item = random.choice(items)
                    line = SalesOrderLine(
                        parent=order,
                        status='planned',
                    )
                    # Ensure JSON defaults and set a minimal item/qty/price snapshot
                    line.ensure_json_defaults()
                    item_blob = dict(line.item or {})
                    item_blob.update({
                        'id_num': item.id,
                        'uuid_item': str(item.uuid) if getattr(item, 'uuid', None) else '',
                        'description': getattr(item, 'name', '') or getattr(item, 'ida', ''),
                        'unit_measure': 'ea',
                    })
                    qty = (li + 1) * 2
                    qty_blob = dict(line.quantity or {})
                    qty_blob.update({
                        'placed': qty,
                        'backlog': qty,
                        'remaining': qty,
                        'precision': 0,
                    })
                    unit_price = 10.0 + li * 5.0
                    price_blob = dict(line.price or {})
                    price_blob.update({
                        'unit': unit_price,
                        'extended': unit_price * qty,
                        'precision': 2,
                    })
                    # Initial save to get PK and mirror parent_ref_id
                    line.save()
                    # Persist JSON blobs via queryset.update to avoid static assignment warnings
                    SalesOrderLine.objects.filter(pk=line.pk).update(
                        item=item_blob,
                        quantity=qty_blob,
                        price=price_blob,
                    )
                    created_lines += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {created_orders} sales orders with {created_lines} lines"
        ))
"""
Management command to seed SalesOrders with SalesOrderLines.
Usage:
  python manage.py seed_transactions --orders 2 --lines 3
Creates demo orders and lines so detail GET embeds non-empty sales_order_lines.
"""
