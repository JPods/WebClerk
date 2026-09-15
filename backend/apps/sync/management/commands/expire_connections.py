"""expire_connections — disable Connections past their sunset date.

Implements readmes/50-security-policy-webclerk.md §6:
  "Expired Connections are disabled automatically — they are attack surface
  with no business purpose. Owner notified to renew or confirm removal."

Usage:
  python manage.py expire_connections              # preview (dry run)
  python manage.py expire_connections --apply       # disable expired connections
  python manage.py expire_connections --all         # include already-inactive

Run nightly via cron or Celery Beat.

Sunset date is stored in config.sunset or config.sunset_date (ISO 8601 or epoch ms).
Connections without a sunset date are flagged as warnings.

Established: 2026-09-10
"""
import logging
from datetime import datetime, timezone

from django.core.management.base import BaseCommand
from django.utils import timezone as dj_tz

logger = logging.getLogger('console')


class Command(BaseCommand):
    help = 'Disable Connections past their sunset date'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help='Actually disable expired connections (default is dry run)',
        )
        parser.add_argument(
            '--all', action='store_true',
            help='Include already-inactive connections in the report',
        )

    def handle(self, *args, **options):
        from apps.sync.models import Connection

        apply = options['apply']
        include_all = options['all']

        qs = Connection.objects.all()
        if not include_all:
            qs = qs.filter(is_active=True)

        now = datetime.now(timezone.utc)
        now_ms = int(now.timestamp() * 1000)

        expired = []
        no_sunset = []
        active = []

        for conn in qs:
            config = conn.config or {}
            sunset = config.get('sunset') or config.get('sunset_date')

            if not sunset:
                no_sunset.append(conn)
                continue

            expired_flag = False

            # Handle ISO 8601 string
            if isinstance(sunset, str):
                try:
                    sunset_dt = datetime.fromisoformat(sunset.replace('Z', '+00:00'))
                    if sunset_dt < now:
                        expired_flag = True
                except (ValueError, TypeError):
                    self.stderr.write(
                        f"  WARNING: Connection {conn.id} ({conn.name}) has "
                        f"unparseable sunset date: {sunset}"
                    )
                    continue

            # Handle epoch milliseconds
            elif isinstance(sunset, (int, float)):
                if sunset < now_ms:
                    expired_flag = True

            if expired_flag:
                expired.append(conn)
            else:
                active.append(conn)

        # Report
        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(f"Connection Sunset Audit — {now.isoformat()}")
        self.stdout.write(f"{'=' * 60}\n")

        if expired:
            self.stdout.write(self.style.ERROR(
                f"\nEXPIRED ({len(expired)}):"
            ))
            for conn in expired:
                sunset = (conn.config or {}).get('sunset') or (conn.config or {}).get('sunset_date')
                self.stdout.write(
                    f"  [{conn.id}] {conn.name} — sunset: {sunset} — "
                    f"active: {conn.is_active}"
                )
                if apply and conn.is_active:
                    conn.is_active = False
                    conn.save(update_fields=['is_active'])
                    self.stdout.write(self.style.WARNING(
                        f"    → DISABLED"
                    ))
                    logger.warning(
                        "[SECURITY] Connection %s (%s) disabled — past sunset date %s",
                        conn.id, conn.name, sunset,
                    )

        if no_sunset:
            self.stdout.write(self.style.WARNING(
                f"\nNO SUNSET DATE ({len(no_sunset)}):"
            ))
            for conn in no_sunset:
                self.stdout.write(
                    f"  [{conn.id}] {conn.name} — type: {conn.type} — "
                    f"active: {conn.is_active}"
                )
            self.stdout.write(
                "\n  ⚠ Connections without sunset dates are security risks."
                "\n  Add config.sunset (ISO 8601) to each connection.\n"
            )

        if active:
            self.stdout.write(self.style.SUCCESS(
                f"\nACTIVE ({len(active)}):"
            ))
            for conn in active:
                sunset = (conn.config or {}).get('sunset') or (conn.config or {}).get('sunset_date')
                self.stdout.write(
                    f"  [{conn.id}] {conn.name} — sunset: {sunset}"
                )

        # Summary
        self.stdout.write(f"\n{'─' * 60}")
        self.stdout.write(
            f"Total: {len(expired)} expired, {len(no_sunset)} no sunset, "
            f"{len(active)} active"
        )
        if expired and not apply:
            self.stdout.write(self.style.WARNING(
                "\nDry run — use --apply to disable expired connections"
            ))
        self.stdout.write("")
