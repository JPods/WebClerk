from django.core.management.base import BaseCommand
from apps.products.services.inventory_reservations import release_expired


class Command(BaseCommand):
    help = 'Expire stale inventory reservations (returns availability).'

    def add_arguments(self, parser):  # pragma: no cover
        parser.add_argument('--batch', type=int, default=500)

    def handle(self, *args, **opts):  # pragma: no cover
        summary = release_expired(batch=opts['batch'])
        self.stdout.write(self.style.SUCCESS(f"expire_inventory_reservations: {summary}"))
