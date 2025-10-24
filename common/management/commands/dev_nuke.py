from __future__ import annotations
from django.core.management.base import BaseCommand
from apps.core.fixtures.seed import seed_all


class Command(BaseCommand):
    help = "DEV ONLY: drop data (flush+migrate) and reseed in one step."

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
            migrate=True,
        )
        self.stdout.write(self.style.SUCCESS(f"Dev nuke + reseed complete: {result}"))
