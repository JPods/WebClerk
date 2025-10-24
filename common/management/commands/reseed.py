from __future__ import annotations
from typing import List, Optional
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from apps.core.fixtures.seed import seed_all, DEFAULT_SUPERUSER_EMAILS

def _emails_from_count(n: Optional[int]) -> List[str]:
    if not n or n <= 0:
        return list(DEFAULT_SUPERUSER_EMAILS)
    return [f"{i}@{i}.com" for i in range(1, n + 1)]

class Command(BaseCommand):
    help = "Unified reseed: optional flush/migrate, superusers, registered seeders, auto-seeding, connections."

    def add_arguments(self, parser):
        parser.add_argument("--full", action="store_true", help="Flush + migrate before seeding.")
        parser.add_argument("--no-flush", action="store_true", help="Skip flush when not using --full.")
        parser.add_argument("--per-model", type=int, default=5)
        parser.add_argument("--superusers", type=int, default=3)
        parser.add_argument("--email", action="append", dest="emails")
        parser.add_argument("--with-connections", action="store_true", default=True)
        parser.add_argument("--no-connections", action="store_false", dest="with_connections")

    def handle(self, *args, **opts):
        host = settings.DATABASES["default"].get("HOST") or ""
        if host not in ("", "localhost", "127.0.0.1") and not settings.DEBUG:
            raise CommandError(f"Refusing to reseed non-local DB host={host!r} with DEBUG=False.")
        flush = bool(opts["full"]) or (not opts["no_flush"] and not opts["full"])
        migrate = bool(opts["full"])
        emails = opts.get("emails") or _emails_from_count(opts.get("superusers", 3))
        result = seed_all(
            per_model=opts["per_model"],
            superuser_emails=emails,
            with_connections=opts["with_connections"],
            flush=flush,
            migrate=migrate,
        )
        self.stdout.write(self.style.SUCCESS(f"Reseed complete: {result}"))