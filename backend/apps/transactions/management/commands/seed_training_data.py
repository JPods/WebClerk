"""Seed training/demo data: zzitem + zzCustomer.

These records are permanent fixtures for Alice's training flow.
Not deleted by cleanup_training — they're the stage, not the actors.
Filter from reports: WHERE ida NOT LIKE 'zz%'

Usage:
    python manage.py seed_training_data
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create zzitem and zzCustomer training fixtures"

    def handle(self, *args, **options):
        from apps.products.models import Item
        from apps.products.models.warehouse import Warehouse
        from apps.products.models.inventory_layer import InventoryLayer
        from apps.orgs.models import OrgBase
        from apps.core.models import Contact

        # ── zzCustomer ────────────────────────────────────────────────
        customer, created = OrgBase.objects.get_or_create(
            ida='zzCustomer',
            defaults={
                'display_name': 'Training Customer',
                'org_type': 'customer',
                'is_active': True,
                'email': 'training@example.local',
                'phone': '555-0000',
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created zzCustomer (id={customer.pk})"))
        else:
            self.stdout.write(f"zzCustomer already exists (id={customer.pk})")

        # ── zzContact ─────────────────────────────────────────────────
        contact, created = Contact.objects.get_or_create(
            email='zztraining@example.local',
            defaults={
                'name_first': 'Training',
                'name_last': 'User',
                'is_active': True,
                'customer': customer,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created zzContact (id={contact.pk})"))

        # ── zzitem ────────────────────────────────────────────────────
        item, created = Item.objects.get_or_create(
            ida='zzitem',
            defaults={
                'description': 'Training Widget — not for real orders',
                'is_active': True,
                'price': {
                    'base': 25.00,
                    'retail': 25.00,
                    'wholesale': 20.00,
                    'distributor': 15.00,
                    'sample': 10.00,
                    'qty_breaks': [
                        {'min_qty': 10, 'unit_price': 22.50},
                        {'min_qty': 50, 'unit_price': 20.00},
                        {'min_qty': 100, 'unit_price': 17.50},
                    ],
                    'currency': 'USD',
                },
                'cost': {
                    'standard': 10.00,
                    'avg': 10.00,
                    'last': 10.00,
                },
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created zzitem (id={item.pk})"))
        else:
            self.stdout.write(f"zzitem already exists (id={item.pk})")

        # ── Warehouse + inventory ─────────────────────────────────────
        wh, _ = Warehouse.objects.get_or_create(
            code='ZZTRAIN',
            defaults={'name': 'Training Warehouse', 'is_active': True},
        )

        layer, created = InventoryLayer.objects.get_or_create(
            item=item,
            warehouse=wh,
            defaults={
                'quantity': {'on_hand': 100, 'on_so': 0, 'on_po': 0},
                'cost': {'unit_po': 10.0, 'moving_avg': 10.0},
                'lot': 'TRAINING',
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(
                f"Created inventory: 100 on_hand for zzitem at {wh.name}"
            ))
        else:
            self.stdout.write(f"Inventory layer already exists (id={layer.pk})")

        self.stdout.write(self.style.SUCCESS(
            f"\nTraining data ready:"
            f"\n  Customer: zzCustomer (id={customer.pk})"
            f"\n  Contact:  zztraining@example.local (id={contact.pk})"
            f"\n  Item:     zzitem (id={item.pk})"
            f"\n  Warehouse: ZZTRAIN"
            f"\n  Inventory: 100 on_hand"
            f"\n\nRun training: POST /wcapi/manage/ "
            f"{{action:'run_training_flow', params:{{customer_id:{customer.pk}, item_id:{item.pk}}}}}"
        ))
