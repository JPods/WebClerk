from __future__ import annotations
from django.core.management.base import BaseCommand
from apps.core.fixtures import seed_all


class Command(BaseCommand):
    help = "Quick reset: flush DB and reseed without nuking migrations."

    def add_arguments(self, parser):
        parser.add_argument("--per-model", type=int, default=5)
        parser.add_argument("--superusers", type=int, default=3)
        parser.add_argument("--no-connections", action="store_true")

    def handle(self, *args, **opts):
        emails = [f"{i}@{i}.com" for i in range(1, int(opts["superusers"]) + 1)]
        result = seed_all(
            per_model=opts["per_model"],
            superuser_emails=emails,
            with_connections=not opts["no_connections"],
            flush=True,
            migrate=False,
        )
        self.stdout.write(self.style.SUCCESS(f"Quick reset complete: {result}"))
