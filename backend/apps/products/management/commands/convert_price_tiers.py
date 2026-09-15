"""
Management command to convert Item.price from tiers[] to flat price-level keys.

For every Item:
  1. Read price.base
  2. Remove the "tiers" list
  3. Insert flat keys derived from base:
       retail      = 100% of base
       wholesale   =  90% of base
       distributor =  75% of base
       sample      =  70% of base

Usage:
    python manage.py convert_price_tiers --dry-run        # preview changes
    python manage.py convert_price_tiers                  # apply changes
    python manage.py convert_price_tiers --item-id 42     # single item
"""

from django.core.management.base import BaseCommand
from apps.products.models import Item


# base multipliers for each price level
PRICE_LEVELS = {
    "retail":      1.00,
    "wholesale":   0.90,
    "distributor": 0.75,
    "sample":      0.70,
}


class Command(BaseCommand):
    help = "Convert Item.price.tiers[] to flat price-level keys (retail, wholesale, distributor, sample)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without saving.",
        )
        parser.add_argument(
            "--item-id",
            type=int,
            default=None,
            help="Process a single Item by ID.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        item_id = options["item_id"]

        qs = Item.objects.all()
        if item_id:
            qs = qs.filter(id=item_id)

        total = qs.count()
        updated = 0
        skipped = 0

        self.stdout.write(f"Processing {total} item(s)...  {'(DRY RUN)' if dry_run else ''}")

        for item in qs.iterator():
            price = item.price or {}
            base = price.get("base")

            if base is None:
                skipped += 1
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(f"  SKIP Item {item.id} ({getattr(item, 'ida', '')}) — base is None")
                    )
                continue

            try:
                base = float(base)
            except (TypeError, ValueError):
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(f"  SKIP Item {item.id} — base={base!r} not numeric")
                )
                continue

            # Build new price dict preserving base, msrp, currency, qty_breaks, history
            new_price = {
                "base": base,
                "msrp": price.get("msrp") if price.get("msrp") else base,
            }

            # Add flat price-level keys
            for level, multiplier in PRICE_LEVELS.items():
                new_price[level] = round(base * multiplier, 2)

            # Carry forward non-tier keys
            new_price["currency"] = price.get("currency", "USD")
            new_price["qty_breaks"] = price.get("qty_breaks", [])
            new_price["history"] = price.get("history", [])

            # tiers is deliberately NOT carried forward

            if dry_run:
                old_tiers = price.get("tiers", [])
                self.stdout.write(
                    f"  Item {item.id:>5} ({getattr(item, 'ida', ''):>15})  "
                    f"base={base:>10.2f}  "
                    f"retail={new_price['retail']:>10.2f}  "
                    f"wholesale={new_price['wholesale']:>10.2f}  "
                    f"distributor={new_price['distributor']:>10.2f}  "
                    f"sample={new_price['sample']:>10.2f}  "
                    f"old_tiers={old_tiers}"
                )
            else:
                item.price = new_price
                item.save(update_fields=["price"])

            updated += 1

        tag = "Would update" if dry_run else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {tag} {updated} item(s), skipped {skipped}."
            )
        )
