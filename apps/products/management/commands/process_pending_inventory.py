from django.core.management.base import BaseCommand
from apps.products.services.inventory_adjustment_processor import process_pending_inventory


class Command(BaseCommand):
    help = "Process pending inventory adjustments (apply issues queued while stacks were locked)."

    def add_arguments(self, parser):  # pragma: no cover
        parser.add_argument('--limit', type=int, default=100)
        parser.add_argument('--apply-insufficient', action='store_true', help='Force apply even if remaining < qty (may drive negative).')
        parser.add_argument('--cancel-on-insufficient', action='store_true', help='Cancel rows that cannot be applied due to insufficient qty.')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):  # pragma: no cover
        summary = process_pending_inventory(
            limit=opts['limit'],
            apply_insufficient=bool(opts.get('apply_insufficient')),
            cancel_on_insufficient=bool(opts.get('cancel_on_insufficient')),
            dry_run=bool(opts.get('dry_run')),
        )
        self.stdout.write(self.style.SUCCESS(f"process_pending_inventory: {summary}"))
