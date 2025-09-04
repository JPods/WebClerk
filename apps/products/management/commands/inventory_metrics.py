from django.core.management.base import BaseCommand
from django.utils import timezone
import json

from apps.products.services.inventory_metrics import summarize_inventory_metrics


class Command(BaseCommand):
    help = 'Print summarized inventory & reservation operational metrics.'

    def add_arguments(self, parser):  # pragma: no cover
        parser.add_argument('--samples', action='store_true', help='Include sample pending adjustments and reservations')
        parser.add_argument('--sample-limit', type=int, default=5)
        parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON')

    def handle(self, *args, **opts):  # pragma: no cover
        include_samples = bool(opts.get('samples'))
        sample_limit = int(opts.get('sample_limit') or 5)
        metrics = summarize_inventory_metrics(include_samples=include_samples, sample_limit=sample_limit)
        dumped = json.dumps(metrics, indent=2 if opts.get('pretty') else None, default=str)
        self.stdout.write(dumped)
