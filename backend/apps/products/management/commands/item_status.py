"""
Management command to check item and pending status for testing.

Usage:
    python manage.py item_status 249 250 251
    python manage.py item_status 249 --pending
    python manage.py item_status --all-pending
"""
import json
from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.products.models import Item
from apps.core.models import Pending


class Command(BaseCommand):
    help = "Check item quantity and pending record status"

    def add_arguments(self, parser):
        parser.add_argument(
            'item_ids',
            nargs='*',
            type=int,
            help='Item IDs to check',
        )
        parser.add_argument(
            '--pending',
            action='store_true',
            help='Show pending records for these items',
        )
        parser.add_argument(
            '--all-pending',
            action='store_true',
            help='Show all unprocessed pending records',
        )

    def _ordered_quantity(self, q: dict) -> dict:
        """Return quantity with keys in logical order."""
        key_order = (
            'on_hand', 'available', 'allocated',
            'sell_default', 'purchase_default',
            'on_po', 'on_wo', 'on_so', 'invoiced',
        )
        return {k: q.get(k, 0) for k in key_order if k in q}

    def handle(self, *args, **options):
        item_ids = options['item_ids']
        show_pending = options['pending']
        all_pending = options['all_pending']

        # Show all unprocessed pending records
        if all_pending:
            pending_qs = Pending.objects.filter(
                model_name='item',
                dt_processed=0,
            ).order_by('dt_created')[:50]
            
            self.stdout.write(f"\n{'='*70}")
            self.stdout.write(f"  UNPROCESSED PENDING RECORDS ({pending_qs.count()})")
            self.stdout.write(f"{'='*70}")
            
            for p in pending_qs:
                data = p.config or {}
                buckets = {k: data.get(k, 0) for k in ['on_so', 'on_po', 'on_wo', 'invoiced'] if data.get(k, 0) != 0}
                self.stdout.write(
                    f"  #{p.pk}: item={data.get('item_id')} "
                    f"purpose={p.purpose} "
                    f"deltas={buckets}"
                )
            return

        if not item_ids:
            self.stdout.write(self.style.WARNING("No item IDs provided. Usage: python manage.py item_status 249 250 251"))
            return

        self.stdout.write(f"\n{'='*70}")
        self.stdout.write(f"  ITEM STATUS CHECK")
        self.stdout.write(f"{'='*70}")

        for item_id in item_ids:
            try:
                item = Item.objects.get(pk=item_id)
                q = self._ordered_quantity(item.quantity or {})
                
                self.stdout.write(f"\n  Item #{item.pk} ({item.ida or item.sku or item.name})")
                self.stdout.write(f"  {'-'*50}")
                self.stdout.write(f"  Quantity: {json.dumps(q)}")
                
                if show_pending:
                    # Show pending records for this item
                    pending_qs = Pending.objects.filter(
                        model_name='item',
                        record_id=str(item_id),
                    ).order_by('-dt_created')[:10]
                    
                    if pending_qs.exists():
                        self.stdout.write(f"  Pending records ({pending_qs.count()}):")
                        for p in pending_qs:
                            data = p.config or {}
                            status = "✓ processed" if p.dt_processed else "⏳ unprocessed"
                            buckets = {k: data.get(k, 0) for k in ['on_so', 'on_po', 'on_wo', 'invoiced'] if data.get(k, 0) != 0}
                            self.stdout.write(
                                f"    #{p.pk}: {p.purpose} {buckets} [{status}]"
                            )
                    else:
                        self.stdout.write(f"  Pending records: (none)")
                        
            except Item.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"  Item #{item_id}: NOT FOUND"))

        self.stdout.write(f"\n{'='*70}\n")
