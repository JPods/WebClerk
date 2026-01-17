"""
Process pending transaction line inventory changes.

Applies deferred inventory quantity updates from Pending records created
by the LineItemService when transaction lines are added, modified, or deleted.

This processor is designed to reduce lock contention on Item records by
batching and applying changes when records are not locked.

Usage:
    python manage.py process_line_item_pending --limit 200
    python manage.py process_line_item_pending --dry-run
"""

from django.core.management.base import BaseCommand
from apps.transactions.services.pending_inventory_processor import (
    process_line_item_pending,
)


class Command(BaseCommand):
    help = "Process pending line item inventory changes (qty_on_so, qty_on_po, etc.)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of pending records to process per run.'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate processing without making changes.'
        )
        parser.add_argument(
            '--item-id',
            type=int,
            default=None,
            help='Process pending records for a specific item only.'
        )
        parser.add_argument(
            '--force-locked',
            action='store_true',
            help='Attempt to process even if items appear locked (use with caution).'
        )

    def handle(self, *args, **opts):
        summary = process_line_item_pending(
            limit=opts['limit'],
            dry_run=bool(opts.get('dry_run')),
            item_id=opts.get('item_id'),
            force_locked=bool(opts.get('force_locked')),
        )
        
        if opts.get('dry_run'):
            self.stdout.write(self.style.WARNING(f"[DRY RUN] {summary}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"process_line_item_pending: {summary}"))
