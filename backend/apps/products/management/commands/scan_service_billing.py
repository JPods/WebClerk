from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.products.models.service import Service


class Command(BaseCommand):
    help = "Scan Service.billing schemas for issues (currency, duplicate tiers, negatives); optional --fix to normalize."  # noqa

    def add_arguments(self, parser):  # pragma: no cover
        parser.add_argument("--fix", action="store_true", help="Apply normalization fixes where possible")
        parser.add_argument("--limit", type=int, default=0, help="Limit number of rows processed")

    def handle(self, *args, **options):  # pragma: no cover
        qs = Service.objects.all().order_by("id")
        limit = options.get("limit") or 0
        if limit:
            qs = qs[:limit]
        issues = 0
        fixed = 0
        for svc in qs.iterator():
            try:
                svc._norm_billing()
                svc._validate_billing()
            except Exception as e:  # collect the error but continue
                issues += 1
                self.stdout.write(f"Service {svc.id} billing validation error: {e}")
                if options.get("fix"):
                    with transaction.atomic():
                        # Attempt normalization & revalidate
                        try:
                            svc._norm_billing()
                            svc._validate_billing()
                            svc.save(update_fields=["billing", "dt_modified"])  # type: ignore[arg-type]
                            fixed += 1
                        except Exception as e2:  # noqa
                            self.stdout.write(f"  Fix attempt failed: {e2}")
        self.stdout.write(f"Scan complete: issues={issues} fixed={fixed}")