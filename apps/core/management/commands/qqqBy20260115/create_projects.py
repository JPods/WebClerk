"""Management command to seed Project records for quick testing."""

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from apps.transactions.models.project import (
    ATTENTION_CHOICES,
    STATUS_CHOICES,
    Project,
    default_logistics,
    default_tasks,
)


class Command(BaseCommand):
    help = "Create ten Project rows with sensible defaults for development environments."

    def add_arguments(self, parser):
        parser.add_argument(
            "--attention",
            default="Bill",
            help="Attention value to assign; defaults to Bill per prompt.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview the payload without persisting records.",
        )

    def handle(self, *args, **options):
        attention_value = options["attention"]
        dry_run = options["dry_run"]

        status_values = [choice[0] for choice in STATUS_CHOICES]
        valid_attention_values = {choice[0] for choice in ATTENTION_CHOICES}
        fallback_attention = next(iter(valid_attention_values)) if valid_attention_values else attention_value
        attention_requires_fallback = attention_value not in valid_attention_values
        if attention_requires_fallback:
            self.stdout.write(
                self.style.WARNING(
                    f"Attention '{attention_value}' is not a valid choice; using '{fallback_attention}' for the model field and storing the requested label in data.attention_label."
                )
            )
        today = timezone.localdate()
        # Compute the first Wednesday on or after today.
        days_until_wednesday = (2 - today.weekday()) % 7
        first_wednesday = today + timedelta(days=days_until_wednesday)

        timestamp_token = timezone.now().strftime("%Y%m%d%H%M%S")
        pending_records = []
        for index in range(1, 11):
            situation_date = first_wednesday + timedelta(weeks=index - 1)
            status_value = status_values[(index - 1) % len(status_values)]
            priority_value = ((index - 1) % 5) + 1
            intent = f"Kanban Flow {situation_date.strftime('%Y-%m-%d')} {timestamp_token}-{index:02d}"
            slug = slugify(intent)[:180]
            resolved_attention = attention_value if not attention_requires_fallback else fallback_attention

            tasks_payload = default_tasks()
            tasks_payload["items"] = [
                {"id": 1, "title": "Kickoff session", "done": False, "weight": 1},
                {"id": 2, "title": "Draft project brief", "done": index % 2 == 0, "weight": 2},
            ]

            logistics_payload = default_logistics()
            logistics_payload.update(
                {
                    "budget": float(25000 + index * 7500),
                    "deadline": int((timezone.now() + timedelta(days=30 + index * 5)).timestamp()),
                    "timezone": "UTC",
                    "resources": ["project_manager", "analyst"],
                }
            )

            pending_records.append(
                {
                    "intent": intent,
                    "situation": situation_date.isoformat(),
                    "category": f"kanban_{situation_date.isoformat()}",
                    "attention": resolved_attention,
                    "status": status_value,
                    "priority": priority_value,
                    "tasks": tasks_payload,
                    "logistics": logistics_payload,
                    "slug": slug,
                    "config": {"attention_label": attention_value},
                }
            )

        if dry_run:
            for payload in pending_records:
                self.stdout.write(
                    f"Preview -> intent={payload['intent']} attention={payload['attention']} (label={attention_value}) status={payload['status']}"
                )
            self.stdout.write(self.style.WARNING("Dry run only; no Project rows were created."))
            return

        created = []
        with transaction.atomic():
            for payload in pending_records:
                project = Project.objects.create(**payload)
                created.append(project)

        for project in created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created Project id={project.id} intent='{project.intent}' attention={project.attention}"
                )
            )

        self.stdout.write(self.style.SUCCESS("Finished creating ten Project records."))
