"""
Management command to populate ida for all models (except Item) using generate_ida(pk).

For Item records use:  python manage.py populate_item_ida  (sets ida = sku)

Usage:
    python manage.py set_all_ida_from_pk
    python manage.py set_all_ida_from_pk --dry-run
    python manage.py set_all_ida_from_pk --overwrite   # replace existing ida values
    python manage.py set_all_ida_from_pk --batch-size 500
    python manage.py set_all_ida_from_pk --app products  # only one app
"""
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.products.models import Item
from common.ida import generate_ida


def _has_ida_field(model) -> bool:
    """Return True if the model has a writable 'ida' CharField (not a property)."""
    for field in model._meta.get_fields():
        if getattr(field, "name", None) == "ida" and hasattr(field, "column"):
            return True
    return False


class Command(BaseCommand):
    help = "Populate ida = generate_ida(pk) for all models except Item"

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
        parser.add_argument(
            "--app",
            dest="app_label",
            default=None,
            help="Limit to a single app label (e.g. 'accounts', 'orgs')",
        )
        parser.add_argument(
            "--prefix",
            dest="prefix",
            default=None,
            help="Override ida prefix (e.g. 'ida'). Default: uses environment-derived prefix via generate_ida().",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        overwrite = options["overwrite"]
        batch_size = options["batch_size"]
        app_label_filter = options.get("app_label")
        prefix_override = options.get("prefix")  # e.g. "ida" for literal "ida-{pk}"

        all_models = apps.get_models()

        total_updated = 0
        total_skipped = 0

        for model in all_models:
            # Skip Item — handled separately by populate_item_ida
            if model is Item:
                continue

            # Optionally filter by app label
            if app_label_filter and model._meta.app_label != app_label_filter:
                continue

            # Only process models with a real 'ida' db column
            if not _has_ida_field(model):
                continue

            label = f"{model._meta.app_label}.{model.__name__}"

            if overwrite:
                qs = model.objects.all()
            else:
                qs = model.objects.filter(ida="")

            count = qs.count()
            if count == 0:
                self.stdout.write(f"  {label}: no records to update")
                continue

            self.stdout.write(f"  {label}: {count} records to update")

            if dry_run:
                sample = qs[:5]
                for obj in sample:
                    new_ida = generate_ida(obj.pk, prefix=prefix_override)
                    self.stdout.write(f"    Would set pk={obj.pk}: ida='{obj.ida}' -> '{new_ida}'")
                if count > 5:
                    self.stdout.write(f"    ... and {count - 5} more")
                total_skipped += count
                continue

            # Batch update via queryset update() to avoid triggering save() signals
            pks = list(qs.values_list("pk", flat=True))
            updated_count = 0
            errors = 0

            for i in range(0, len(pks), batch_size):
                batch = pks[i : i + batch_size]
                try:
                    with transaction.atomic():
                        for pk in batch:
                            new_ida = generate_ida(pk, prefix=prefix_override)
                            model.objects.filter(pk=pk).update(ida=new_ida)
                            updated_count += 1
                except Exception as exc:
                    errors += 1
                    self.stdout.write(
                        self.style.ERROR(f"    Error on batch starting pk={batch[0]}: {exc}")
                    )

            total_updated += updated_count
            status_msg = f"    Updated {updated_count}"
            if errors:
                status_msg += f", {errors} errors"
            self.stdout.write(self.style.SUCCESS(status_msg))

        if dry_run:
            self.stdout.write(self.style.WARNING(f"\nDRY RUN — {total_skipped} records would be updated"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nDone — {total_updated} records updated across all models"))
