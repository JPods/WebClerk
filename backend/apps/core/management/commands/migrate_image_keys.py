"""Rename metadata.images keys: display→md, hires→hr across all models.

Applies to every table inheriting BaseModel (common.models.BaseModel)
that has a metadata JSONB column with an images dict.

Also initializes metadata.documents=[] where missing.

Usage:
    ./bin/python manage.py migrate_image_keys --dry-run
    ./bin/python manage.py migrate_image_keys
"""
from django.core.management.base import BaseCommand
from django.apps import apps


class Command(BaseCommand):
    help = "Rename metadata.images keys (display→md, hires→hr) and init metadata.documents"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report counts without writing")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        total_updated = 0

        # Find all concrete models with a metadata JSONField
        for model in apps.get_models():
            field_names = [f.name for f in model._meta.get_fields()]
            if "metadata" not in field_names:
                continue
            # Skip proxy models, unmanaged, and non-concrete
            if model._meta.proxy or not model._meta.managed:
                continue

            table = model._meta.db_table
            try:
                qs = model.objects.all()
                count = 0

                for record in qs.iterator(chunk_size=500):
                    meta = record.metadata
                    if not isinstance(meta, dict):
                        continue

                    changed = False
                    images = meta.get("images")
                    if isinstance(images, dict):
                        # display → md
                        if "display" in images and "md" not in images:
                            images["md"] = images.pop("display")
                            changed = True
                        elif "display" in images:
                            del images["display"]
                            changed = True

                        # hires → hr
                        if "hires" in images and "hr" not in images:
                            images["hr"] = images.pop("hires")
                            changed = True
                        elif "hires" in images:
                            del images["hires"]
                            changed = True

                    # Init documents list if missing
                    if "documents" not in meta:
                        meta["documents"] = []
                        changed = True

                    if changed:
                        count += 1
                        if not dry_run:
                            model.objects.filter(pk=record.pk).update(metadata=meta)

                if count:
                    tag = "[DRY RUN] " if dry_run else ""
                    self.stdout.write(f"  {tag}{table}: {count} records updated")
                    total_updated += count
            except Exception as e:
                self.stderr.write(f"  SKIP {table}: {e}")

        tag = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(f"\n{tag}Total: {total_updated} records updated"))
