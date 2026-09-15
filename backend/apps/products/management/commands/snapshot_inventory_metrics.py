from django.core.management.base import BaseCommand
from apps.products.services.inventory.inventory_metrics import snapshot_inventory_metrics
import json


class Command(BaseCommand):
    help = 'Persist a snapshot of current inventory metrics.'

    def add_arguments(self, parser):  # pragma: no cover
        parser.add_argument('--samples', action='store_true', help='Include sample rows in snapshot metrics JSON')

    def handle(self, *args, **opts):  # pragma: no cover
        snap = snapshot_inventory_metrics(include_samples=bool(opts.get('samples')))
        # Model field is dt_created
        self.stdout.write(json.dumps({'id': snap.id, 'dt_created': snap.dt_created.isoformat()}))
