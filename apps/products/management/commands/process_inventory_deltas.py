from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from apps.core.models.pending import Pending
from apps.products.models.item import Item


class Command(BaseCommand):
    help = 'Process inventory delta records to update item quantities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of deltas to process in each batch'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without making changes'
        )
        parser.add_argument(
            '--item-id',
            type=int,
            help='Process deltas for specific item only'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        item_id = options['item_id']

        # Query unprocessed deltas (Pending records with purpose='inventory_delta' and dt_processed=0)
        queryset = Pending.objects.filter(
            model_name='inventory_delta',
            purpose='inventory_delta',
            dt_processed=0
        )
        if item_id:
            # Filter by item_id in the data JSON field
            queryset = queryset.extra(
                where=["(data->>'item_id')::int = %s"],
                params=[item_id]
            )

        total_deltas = queryset.count()
        if total_deltas == 0:
            self.stdout.write('No unprocessed inventory deltas found.')
            return

        self.stdout.write(f'Found {total_deltas} unprocessed inventory deltas.')

        if dry_run:
            self.stdout.write('DRY RUN - No changes will be made.')
            # Show summary
            self._show_delta_summary(queryset)
            return

        # Process in batches
        processed = 0
        updated_items = set()

        while True:
            # Get next batch
            batch = list(queryset[:batch_size])
            if not batch:
                break

            # Group by item for efficient updates
            item_deltas = {}
            for delta in batch:
                item_id = delta.config.get('item_id')
                if item_id not in item_deltas:
                    item_deltas[item_id] = []
                item_deltas[item_id].append(delta)

            # Process each item's deltas
            for item_id, deltas in item_deltas.items():
                try:
                    with transaction.atomic():
                        item = Item.objects.select_for_update().get(pk=item_id)

                        # Calculate total changes
                        on_hand_change = sum(Decimal(str(d.config.get('quantity_on_hand_delta', 0))) for d in deltas)
                        on_order_change = sum(Decimal(str(d.config.get('quantity_on_order_delta', 0))) for d in deltas)
                        on_po_change = sum(Decimal(str(d.config.get('quantity_on_po_delta', 0))) for d in deltas)

                        # Update item quantities
                        if hasattr(item, 'quantity'):
                            qty = item.quantity or {}
                        else:
                            qty = {}

                        # Update on-hand
                        current_on_hand = Decimal(str(qty.get('on_hand', 0)))
                        new_on_hand = current_on_hand + on_hand_change
                        qty['on_hand'] = float(new_on_hand)

                        # Update on-order
                        current_on_order = Decimal(str(qty.get('on_order', 0)))
                        new_on_order = current_on_order + on_order_change
                        qty['on_order'] = float(new_on_order)

                        # Update on-PO
                        current_on_po = Decimal(str(qty.get('on_po', 0)))
                        new_on_po = current_on_po + on_po_change
                        qty['on_po'] = float(new_on_po)

                        # Save item
                        item.quantity = qty
                        item.save(update_fields=['quantity', 'dt_modified', 'version'])

                        # Mark deltas as processed
                        for delta in deltas:
                            delta.mark_processed()

                        updated_items.add(item_id)
                        processed += len(deltas)

                        self.stdout.write(
                            f'Updated item {item_id}: '
                            f'on_hand {current_on_hand} -> {new_on_hand}, '
                            f'on_order {current_on_order} -> {new_on_order}, '
                            f'on_po {current_on_po} -> {new_on_po}'
                        )

                except Exception as e:
                    self.stderr.write(f'Error processing item {item_id}: {e}')
                    continue

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {processed} inventory deltas '
                f'for {len(updated_items)} items.'
            )
        )

    def _show_delta_summary(self, queryset):
        """Show summary of deltas that would be processed."""
        # Group by item
        item_summary = {}
        for delta in queryset[:1000]:  # Limit for performance
            item_id = delta.config.get('item_id')
            if item_id not in item_summary:
                # Get item name
                try:
                    item = Item.objects.get(pk=item_id)
                    item_name = str(item)
                except Item.DoesNotExist:
                    item_name = f"Unknown Item {item_id}"

                item_summary[item_id] = {
                    'item_name': item_name,
                    'deltas': 0,
                    'on_hand_change': Decimal('0'),
                    'on_order_change': Decimal('0'),
                    'on_po_change': Decimal('0')
                }

            summary = item_summary[item_id]
            summary['deltas'] += 1
            summary['on_hand_change'] += Decimal(str(delta.config.get('quantity_on_hand_delta', 0)))
            summary['on_order_change'] += Decimal(str(delta.config.get('quantity_on_order_delta', 0)))
            summary['on_po_change'] += Decimal(str(delta.config.get('quantity_on_po_delta', 0)))

        self.stdout.write('\nDelta summary by item:')
        for item_id, summary in item_summary.items():
            self.stdout.write(
                f"  Item {item_id} ({summary['item_name']}): "
                f"{summary['deltas']} deltas, "
                f"on_hand {summary['on_hand_change']:+.2f}, "
                f"on_order {summary['on_order_change']:+.2f}, "
                f"on_po {summary['on_po_change']:+.2f}"
            )