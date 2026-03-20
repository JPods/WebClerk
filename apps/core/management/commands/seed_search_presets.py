from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.core.constants.model_registry import MODEL_REGISTRY
from apps.core.models import Setting


class Command(BaseCommand):
    help = "Seed standard saved search presets for transaction headers and actions"

    def handle(self, *args, **options):
        transaction_models = [
            meta.key
            for meta in MODEL_REGISTRY.values()
            if meta.kind == "header"
        ]

        transaction_presets = {
            "in_period": {
                "request_filters": {
                    "begin": {"field": "dt_created", "lookup": "gte"},
                    "end": {"field": "dt_created", "lookup": "lte"},
                },
                "ordering": "-dt_created",
                "pagination": {"limit": 50, "offset": 0},
            },
            "current_month": {
                "relative_period": {"field": "dt_created", "preset": "current_month"},
                "ordering": "-dt_created",
                "pagination": {"limit": 50, "offset": 0},
            },
            "current_quarter": {
                "relative_period": {"field": "dt_created", "preset": "current_quarter"},
                "ordering": "-dt_created",
                "pagination": {"limit": 50, "offset": 0},
            },
        }

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

        for model_name in transaction_models:
            for name, data in transaction_presets.items():
                _, was_created = Setting.objects.update_or_create(
                    parent_model=model_name,
                    purpose="search",
                    role="all",
                    name=name,
                    defaults={"data": data, "is_active": True},
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        for name, data in action_presets.items():
            _, was_created = Setting.objects.update_or_create(
                parent_model="action",
                purpose="search",
                role="all",
                name=name,
                defaults={"data": data, "is_active": True},
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