"""Give demo items the cost layers their stock never had — demo data only.

Bill, 2026-09-26: "Fake create layers for existing item inventory. We split some into multiple
layers as varying costs if we want to test that behavior." Demo items were loaded with on_hand
and no layers, so once the applier consumes layers on every decrease (plan §16b) each sale of
them would run short. Two passes:

- **Fill**: for every tracked item whose on_hand exceeds what its layers hold, create layers for
  the difference.
- **Split**: an item still held in one untouched layer (nothing issued from it) has that layer
  divided into two or three at different costs, oldest cheapest, keeping the same total, so FIFO,
  LIFO and average give different answers. wc_demo on 2026-09-26 already had one layer per
  stocked item matching on_hand (53 layers, 5,093 units), so the split is the pass that matters.

It moves no item quantity: layers only, so afterwards Σ layer remaining == on_hand
(check_balances). It refuses unless DATA_SET_KIND is 'demo'. A real install's opening stock
arrives as count workorders through the import door (§17.5); this command is the demo-only
exception, named in the ratchet like fix #2's orphan delete.

    manage.py seed_demo_layers            # report what it would create
    manage.py seed_demo_layers --apply    # create the layers
"""
from decimal import Decimal

from decouple import config
from django.core.management.base import BaseCommand, CommandError

# Every third item splits in three, the next in two; the rest get one layer at the base cost.
SPLITS = {0: (Decimal('0.80'), Decimal('1.00'), Decimal('1.25')),
          1: (Decimal('0.90'), Decimal('1.15')),
          2: (Decimal('1.00'),)}


def _base_cost(item) -> Decimal:
    """The item's own cost; a demo item with none is costed at 60% of its price."""
    cost = item.cost if isinstance(item.cost, dict) else {}
    for key in ('avg', 'last', 'standard', 'landed'):
        value = Decimal(str(cost.get(key) or 0))
        if value > 0:
            return value
    price = item.price if isinstance(getattr(item, 'price', None), dict) else {}
    base = Decimal(str(price.get('base') or price.get('list') or 0))
    return (base * Decimal('0.60')).quantize(Decimal('0.01')) if base > 0 else Decimal('1.00')


def _parts(qty: Decimal, weights) -> list:
    """Split qty into len(weights) whole-number parts, oldest first; the last takes the rest."""
    n = len(weights)
    if n == 1 or qty < n:
        return [qty]
    share = (qty / n).quantize(Decimal('1'))
    parts = [share] * (n - 1)
    return parts + [qty - sum(parts)]


class Command(BaseCommand):
    help = "Demo only: create cost layers for item stock that has none (some split at varying costs)"

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Create the layers (default: report only)')

    def handle(self, *args, apply=False, **options):
        if config('DATA_SET_KIND', default='live') != 'demo':
            raise CommandError("seed_demo_layers runs on demo data only (DATA_SET_KIND=demo). "
                               "A real install's opening stock arrives as a count workorder.")

        from apps.products.models import Item
        from apps.products.models.inventory_layer import InventoryLayer
        from apps.products.models.warehouse import Warehouse
        from apps.products.services.inventory.inventory_layers import create_layer

        warehouse = Warehouse.objects.filter(is_active=True).order_by('id').first()
        if warehouse is None:
            raise CommandError("No active warehouse to put the layers in.")

        from apps.products.models.inventory_layer import InventoryMovement
        from apps.products.services.inventory.inventory_layers import recalc_average_cost

        planned, created = 0, 0
        n = 0
        for item in Item.objects.order_by('id'):
            if item.is_not_tracked:
                continue
            on_hand = Decimal(str((item.quantity or {}).get('on_hand') or 0))
            held = sum((Decimal(str(layer.remaining_qty()))
                        for layer in InventoryLayer.objects.filter(item_id=item.pk)), Decimal('0'))
            gap = on_hand - held
            if gap <= 0:
                layers = list(InventoryLayer.objects.filter(item_id=item.pk))
                weights = SPLITS[n % 3]
                n += 1
                if len(layers) != 1 or len(weights) == 1:
                    continue
                layer = layers[0]
                q = layer.quantity or {}
                if Decimal(str(q.get('issued') or 0)) or Decimal(str(q.get('scrapped') or 0)):
                    continue                    # a layer that has issued is history; leave it
                received = Decimal(str(q.get('received') or 0))
                parts = _parts(received, weights)
                if len(parts) == 1:
                    continue
                base = Decimal(str((layer.cost or {}).get('landed') or 0)) or _base_cost(item)
                planned += len(parts)
                self.stdout.write(f"{item.ida or item.pk}: split layer {layer.pk} ({received}) into "
                                  + ", ".join(f"{p} @ {(base * w).quantize(Decimal('0.01'))}"
                                              for p, w in zip(parts, weights)))
                if not apply:
                    continue
                # The existing layer keeps the first (oldest, cheapest) part.
                layer.quantity = {**q, 'received': float(parts[0])}
                layer.update_cost_after_receipt(unit_po=float((base * weights[0]).quantize(Decimal('0.01'))))
                layer.save(update_fields=['quantity', 'cost', 'dt_modified', 'version'])
                InventoryMovement.objects.create(
                    item_id=item.pk, warehouse=layer.warehouse, inventory_layer=layer,
                    site_code=layer.warehouse.site_code, movement_type=InventoryMovement.MOVEMENT_ADJUST,
                    quantity=parts[0] - received, reason='Demo split: moved to newer layers',
                    parent_model='')
                for qty, weight in zip(parts[1:], weights[1:]):
                    create_layer(item.pk, layer.warehouse_id, qty, (base * weight).quantize(Decimal('0.01')),
                                 parent_model='', reason='Demo split layer')
                recalc_average_cost(item.pk)
                created += len(parts)
                continue
            weights = SPLITS[n % 3]
            n += 1
            base = _base_cost(item)
            for qty, weight in zip(_parts(gap, weights), weights):
                unit_cost = (base * weight).quantize(Decimal('0.01'))
                planned += 1
                self.stdout.write(f"{item.ida or item.pk}: layer {qty} @ {unit_cost} in {warehouse.name}")
                if apply:
                    create_layer(item.pk, warehouse.pk, qty, unit_cost,
                                 parent_model='', reason='Demo opening layer')
                    created += 1

        verb = 'Created' if apply else 'Would create'
        self.stdout.write(self.style.SUCCESS(f"{verb} {created if apply else planned} layers."))
