"""
Management command to reset Item.quantity for testing transaction flows.

Sets all items to:
- on_hand: 100 (default, configurable)
- available: 100 (computed)  
- allocated: 0
- sell_default: 1
- purchase_default: 1
- on_po: 0
- on_wo: 0
- on_so: 0
- invoiced: 0

Usage:
    python manage.py reset_item_quantities
    python manage.py reset_item_quantities --on-hand 50
    python manage.py reset_item_quantities --dry-run
    python manage.py reset_item_quantities --show  # Display items with ordered quantity
"""
import json
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.products.models import Item


class Command(BaseCommand):
    help = "Reset Item.quantity buckets for testing transaction flows"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be updated without making changes",
        )
        parser.add_argument(
            "--on-hand",
            type=int,
            default=100,
            help="Initial on_hand quantity (default: 100)",
        )
        parser.add_argument(
            "--item-id",
            type=int,
            default=None,
            help="Reset only a specific item by ID",
        )
        parser.add_argument(
            "--show",
            action="store_true",
            help="Display items with quantity in logical key order (no changes)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        on_hand = options["on_hand"]
        item_id = options["item_id"]
        show_only = options["show"]

        # Build queryset
        qs = Item.objects.all()
        if item_id:
            qs = qs.filter(pk=item_id)

        total = qs.count()
        
        if total == 0:
            self.stdout.write(self.style.WARNING("No items found."))
            return

        # Show mode: display items with ordered quantity and exit
        if show_only:
            self.stdout.write(f"Showing {total} items with quantity in logical order:\n")
            for item in qs[:20]:  # Limit to 20 for readability
                self.stdout.write(f"  Item #{item.pk} ({item.sku or item.name}):")
                self.stdout.write(f"    {json.dumps(item.quantity_display, indent=None)}")
            if total > 20:
                self.stdout.write(f"  ... and {total - 20} more")
            return

        self.stdout.write(f"Found {total} items to reset")
        self.stdout.write(f"Setting on_hand={on_hand}, all transaction buckets=0")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes made"))
            # Show sample
            sample = qs[:5]
            for item in sample:
                old_qty = item.quantity or {}
                self.stdout.write(
                    f"  Item #{item.pk} ({item.sku or item.name}): "
                    f"on_hand={old_qty.get('on_hand', 'N/A')} -> {on_hand}"
                )
            if total > 5:
                self.stdout.write(f"  ... and {total - 5} more")
            return

        # Reset quantities - keys in logical order for human readers
        # Physical inventory → Defaults → Transaction buckets (procurement → production → sales → fulfillment)
        new_quantity = dict([
            ("on_hand", on_hand),
            ("available", on_hand),
            ("allocated", 0),
            ("sell_default", 1),
            ("purchase_default", 1),
            ("on_po", 0),
            ("on_wo", 0),
            ("on_so", 0),
            ("invoiced", 0),
        ])

        updated = 0
        errors = 0

        with transaction.atomic():
            for item in qs.iterator():
                try:
                    # Use update() to avoid triggering full save() with history etc
                    Item.objects.filter(pk=item.pk).update(quantity=new_quantity)
                    updated += 1
                except Exception as e:
                    errors += 1
                    self.stderr.write(f"Error updating Item #{item.pk}: {e}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Reset {updated} items: on_hand={on_hand}, "
                f"on_so=0, on_po=0, on_wo=0, invoiced=0"
            )
        )
        if errors:
            self.stdout.write(self.style.ERROR(f"{errors} errors"))
