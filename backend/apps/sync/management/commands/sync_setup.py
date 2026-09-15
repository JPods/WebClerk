"""
Management command to set up sync connections and send test bundles.

Usage:
    # Create the Mac ↔ Andi connection (run on BOTH machines)
    python manage.py sync_setup connect --name "Mac-Andi" --endpoint http://localhost:8000/wcapi/sync/receive/

    # Send a test bundle (creates a Pending record)
    python manage.py sync_setup test --connection "Mac-Andi"

    # Process all pending (same as what Celery does hourly)
    python manage.py sync_setup process

    # Show status of pending records
    python manage.py sync_setup status
"""

import secrets
import time
from django.core.management.base import BaseCommand

from apps.sync.models.connection import Connection
from apps.core.models.pending import Pending


class Command(BaseCommand):
    help = "Set up sync connections and test bundle delivery"

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="action")

        # connect — create or update a connection
        conn = sub.add_parser("connect", help="Create a bidirectional connection")
        conn.add_argument("--name", required=True, help="Connection name (e.g. Mac-Andi)")
        conn.add_argument("--endpoint", required=True, help="Remote receive URL")
        conn.add_argument("--key", help="Shared key (generated if omitted)")

        # test — create a test Pending record
        test = sub.add_parser("test", help="Create a test bundle for delivery")
        test.add_argument("--connection", required=True, help="Connection name")

        # process — run the pending processor now
        sub.add_parser("process", help="Process all pending records now")

        # status — show pending records
        sub.add_parser("status", help="Show pending sync status")

    def handle(self, *args, **options):
        action = options.get("action")
        if action == "connect":
            self._connect(options)
        elif action == "test":
            self._test(options)
        elif action == "process":
            self._process()
        elif action == "status":
            self._status()
        else:
            self.stderr.write("Usage: sync_setup [connect|test|process|status]")

    def _connect(self, options):
        name = options["name"]
        endpoint = options["endpoint"]
        key = options.get("key") or secrets.token_urlsafe(32)

        conn, created = Connection.objects.update_or_create(
            name=name,
            defaults={
                "type": "api",
                "purpose": "sync",
                "status": "active",
                "config": {
                    "endpoint": endpoint,
                    "key": key,
                },
            },
        )

        verb = "Created" if created else "Updated"
        self.stdout.write(f"{verb} connection: {conn.name} (id={conn.id})")
        self.stdout.write(f"  Endpoint: {endpoint}")
        self.stdout.write(f"  Key: {key}")
        self.stdout.write("")
        self.stdout.write("Run on the OTHER machine with the same --key:")
        self.stdout.write(f'  python manage.py sync_setup connect --name "{name}" '
                          f'--endpoint <this-machine-url>/wcapi/sync/receive/ --key "{key}"')

    def _test(self, options):
        conn_name = options["connection"]
        try:
            conn = Connection.objects.get(name=conn_name, is_active=True)
        except Connection.DoesNotExist:
            self.stderr.write(f"Connection '{conn_name}' not found. Run sync_setup connect first.")
            return

        # Auto-increment sequence for this connection
        last_seq = Pending.objects.filter(
            purpose="sync.bundle_out",
            config__connection_id=conn.id,
        ).order_by("-sequence").values_list("sequence", flat=True).first() or 0

        pending = Pending.objects.create(
            purpose="sync.bundle_out",
            name=f"Test handshake → {conn_name}",
            sequence=last_seq + 1,
            config={
                "connection_id": conn.id,
                "test": True,
                "echo": "handshake",
                "payload": {
                    "message": "sync test — this is just a test",
                    "source": conn_name,
                    "dt_created": int(time.time() * 1000),
                },
            },
        )

        self.stdout.write(f"Created test Pending (id={pending.id}, purpose=sync.bundle_out)")
        self.stdout.write(f"  Connection: {conn.name} → {conn.config.get('endpoint', '?')}")
        self.stdout.write("")
        self.stdout.write("To send now:  python manage.py sync_setup process")
        self.stdout.write("Or wait for the next Celery cycle (hourly).")

    def _process(self):
        from apps.sync.services.pending_processor import process_all_pending
        processed, failed, skipped = process_all_pending()
        self.stdout.write(f"Processed: {processed}  Failed: {failed}  Skipped: {skipped}")

    def _status(self):
        pending = Pending.objects.filter(purpose__startswith="sync.", is_active=True)
        unprocessed = pending.filter(dt_processed=0)
        done = pending.filter(dt_processed__gt=0)

        self.stdout.write(f"Sync pending: {unprocessed.count()} unprocessed, {done.count()} completed")
        self.stdout.write("")

        for p in unprocessed.order_by("-dt_created")[:10]:
            attempts = p.attempts or 0
            self.stdout.write(f"  [{p.id}] {p.purpose} — {p.name or '?'} — {attempts} attempts")
            changes = p.changes if isinstance(p.changes, list) else []
            if changes:
                last = changes[-1]
                self.stdout.write(f"         Last: {last.get('result', '?')} — {last.get('message', '')}")
