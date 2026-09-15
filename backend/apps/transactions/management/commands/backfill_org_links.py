"""Backfill refs.links.customer / vendor / manufacturer on existing transactions.

Usage:
    python manage.py backfill_org_links                  # dry-run (default)
    python manage.py backfill_org_links --commit         # actually save
    python manage.py backfill_org_links --models order   # one model only
    python manage.py backfill_org_links --batch 500      # custom batch size
"""

from __future__ import annotations

import time
from django.core.management.base import BaseCommand
from apps.transactions.services.denormalize_org_links import denormalize_org_links
from apps.core.utils import registry

TRANSACTION_MODELS = ("order", "invoice", "proposal", "purchase")


class Command(BaseCommand):
    help = "Backfill refs.links with denormalized org data on transaction records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit",
            action="store_true",
            default=False,
            help="Actually save changes (default is dry-run).",
        )
        parser.add_argument(
            "--models",
            nargs="*",
            default=list(TRANSACTION_MODELS),
            help=f"Which models to process (default: {' '.join(TRANSACTION_MODELS)}).",
        )
        parser.add_argument(
            "--batch",
            type=int,
            default=200,
            help="Batch size for queryset iteration (default 200).",
        )

    def handle(self, *args, **options):
        commit = options["commit"]
        models = options["models"]
        batch_size = options["batch"]

        mode = "COMMIT" if commit else "DRY-RUN"
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"  Backfill org links — {mode}")
        self.stdout.write(f"  Models: {', '.join(models)}")
        self.stdout.write(f"  Batch:  {batch_size}")
        self.stdout.write(f"{'='*60}\n")

        grand_total = 0
        grand_updated = 0
        grand_skipped = 0
        grand_errors = 0
        t0 = time.time()

        for model_key in models:
            Model = registry.resolve(model_key)
            if Model is None:
                self.stderr.write(f"  [SKIP] Unknown model: {model_key}")
                continue

            qs = Model.objects.all().order_by("pk")
            total = qs.count()
            self.stdout.write(f"\n  {model_key}:  {total} records")

            updated = 0
            skipped = 0
            errors = 0

            # Iterate in batches using pk slicing
            last_pk = 0
            while True:
                batch = list(
                    qs.filter(pk__gt=last_pk).order_by("pk")[:batch_size]
                )
                if not batch:
                    break

                for obj in batch:
                    last_pk = obj.pk
                    try:
                        mutated = denormalize_org_links(obj, model_key)
                        if mutated:
                            if commit:
                                obj.save(update_fields=["refs"])
                            updated += 1
                        else:
                            skipped += 1
                    except Exception as exc:
                        errors += 1
                        self.stderr.write(
                            f"    ERROR {model_key} #{obj.pk}: {exc}"
                        )

                # Progress
                processed = updated + skipped + errors
                self.stdout.write(
                    f"    processed {processed}/{total}  "
                    f"(updated={updated} skipped={skipped} errors={errors})",
                    ending="\r",
                )

            self.stdout.write(
                f"    {model_key}: updated={updated}  skipped={skipped}  "
                f"errors={errors}  total={total}          "
            )

            grand_total += total
            grand_updated += updated
            grand_skipped += skipped
            grand_errors += errors

        elapsed = time.time() - t0
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(
            f"  TOTALS:  {grand_total} records, "
            f"{grand_updated} updated, "
            f"{grand_skipped} unchanged, "
            f"{grand_errors} errors"
        )
        self.stdout.write(f"  Elapsed: {elapsed:.1f}s  |  Mode: {mode}")
        if not commit:
            self.stdout.write("  (pass --commit to apply changes)")
        self.stdout.write(f"{'='*60}\n")
