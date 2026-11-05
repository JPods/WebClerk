"""recompute_item_margin — set every item's margin_pct from the one formula (price_resolver).

Item.save sets margin_pct; this is for items saved before 2026-11-05 or after a change to the
company's cost basis. Usage: manage.py recompute_item_margin
"""
from django.core.management.base import BaseCommand

from apps.products.models import Item
from apps.products.services.price_resolver import resolve_cost


class Command(BaseCommand):
    help = "Set every item's margin_pct from price_resolver.resolve_cost"

    def handle(self, *args, **options):
        n = 0
        for item in Item.objects.all().iterator():
            Item.objects.filter(pk=item.pk).update(margin_pct=resolve_cost(item).margin_pct)
            n += 1
        self.stdout.write(f'{n} items recomputed')
