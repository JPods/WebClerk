from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.core.constants.model_registry import MODEL_REGISTRY
from apps.core.models import Setting


class Command(BaseCommand):
    help = "Seed saved search presets for actions"

    def handle(self, *args, **options):
        # Date-range presets (in_period, current_month, current_quarter) are handled
        # by the built-in date_between function — no per-model Setting records needed.

        action_presets = {
            "assigned_to_in_period": {
                "request_keyword": "assigned_to",
                "request_filters": {
                    "begin": {"field": "dt_created", "lookup": "gte"},
                    "end": {"field": "dt_created", "lookup": "lte"},
                },
                "ordering": "-dt_created",
                "pagination": {"limit": 50, "offset": 0},
            },
            "assigned_to_is_active": {
                "request_keyword": "assigned_to",
                "request_filters": {
                    "is_active": {"field": "is_active", "lookup": "exact"},
                },
                "ordering": "-dt_created",
                "pagination": {"limit": 50, "offset": 0},
            },
            "assigned_to_is_active_priority": {
                "request_keyword": "assigned_to",
                "request_filters": {
                    "is_active": {"field": "is_active", "lookup": "exact"},
                    "priority": {"field": "priority", "lookup": "exact"},
                },
                "ordering": "-dt_created",
                "pagination": {"limit": 50, "offset": 0},
            },
        }

        created = 0
        updated = 0

        for name, data in action_presets.items():
            _, was_created = Setting.objects.update_or_create(
                parent_model="action",
                purpose="wc:search",
                role="all",
                name=name,
                defaults={"config": data, "is_active": True},
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded search presets: created={created}, updated={updated}, transaction_models={len(transaction_models)}"
            )
        )