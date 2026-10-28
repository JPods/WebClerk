"""check_inventory_log — the inventory Log against the stock Pendings (log_check.py)."""
import json

from django.core.management.base import BaseCommand

from apps.products.services.inventory.log_check import reconcile_inventory_log


class Command(BaseCommand):
    help = "Check the inventory log against the stock Pendings: matched, log only, pending only"

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30)

    def handle(self, *args, **opts):
        self.stdout.write(json.dumps(reconcile_inventory_log(opts['days']), indent=2, default=str))
