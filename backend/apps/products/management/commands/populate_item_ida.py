"""
Management command to populate Item.ida with Item.sku for all items.

Usage:
    python manage.py populate_item_ida
    python manage.py populate_item_ida --dry-run
    python manage.py populate_item_ida --overwrite  # replace existing ida values
    python manage.py populate_item_ida --batch-size 500
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.products.models import Item


class Command(BaseCommand):
    help = "Populate Item.ida with Item.sku for all items"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be updated without making changes",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing ida values (default: only update empty ida)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Number of records to update per batch (default: 1000)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        overwrite = options["overwrite"]
        batch_size = options["batch_size"]

        # Build queryset based on overwrite flag
        if overwrite:
            # All items with a sku
            qs = Item.objects.filter(sku__isnull=False).exclude(sku="")
        else:
            # Only items with empty ida and a valid sku
            qs = Item.objects.filter(
                sku__isnull=False
            ).exclude(sku="").filter(ida="")

        total = qs.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No items to update."))
            return

        self.stdout.write(f"Found {total} items to update ida = sku")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes made"))
            # Show sample
            sample = qs[:10]
            for item in sample:
                self.stdout.write(f"  Would update Item #{item.pk}: ida='{item.ida}' -> '{item.sku}'")
            if total > 10:
                self.stdout.write(f"  ... and {total - 10} more")
            return

        # Batch update for efficiency
        updated = 0
        errors = 0

        # Use iterator to avoid loading all into memory
        item_pks = list(qs.values_list("pk", flat=True))
        
        for i in range(0, len(item_pks), batch_size):
            batch_pks = item_pks[i : i + batch_size]
            
            try:
                with transaction.atomic():
                    # Update each item in batch - need individual updates since ida = sku per row
                    for pk in batch_pks:
                        try:
                            item = Item.objects.get(pk=pk)
                            if item.sku:
                                item.ida = item.sku
                                # Use update() to avoid triggering full save() logic
                                Item.objects.filter(pk=pk).update(ida=item.sku)
                                updated += 1
                        except Exception as e:
                            errors += 1
                            self.stderr.write(f"Error updating Item #{pk}: {e}")
                            
            except Exception as e:
                errors += len(batch_pks)
                self.stderr.write(f"Batch error: {e}")

            # Progress feedback
            self.stdout.write(f"  Processed {min(i + batch_size, len(item_pks))}/{len(item_pks)}")

        self.stdout.write(
            self.style.SUCCESS(f"Updated {updated} items, {errors} errors")
        )
