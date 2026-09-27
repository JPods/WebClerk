"""Seed the SelfConnection — internal Connection for tools that post bundles
to their own WC3 instance (JSON Tree, Matrix Builder, etc.).

Usage: ./manage.py seed_self_connection
"""
import secrets

from django.core.management.base import BaseCommand
from apps.sync.models.connection import Connection


class Command(BaseCommand):
    help = "Create or update the internal SelfConnection for local bundle posting"

    def handle(self, *args, **options):
        conn, created = Connection.objects.get_or_create(
            ida='self-connection',
            defaults={
                'name': 'SelfConnection',
                'type': 'internal',
                'purpose': 'ingest',
                'status': 'active',
                'config': {
                    'description': 'Internal connection for tools posting bundles to this instance',
                },
            },
        )
        if not conn.sync_key:
            # A random key, never the literal 'self-connection' (import plan §17.5): nothing in a
            # browser holds it; local tools post bundles as their signed-in user.
            conn.set_sync_key(secrets.token_urlsafe(32))
            conn.save(update_fields=['encryption'])
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created SelfConnection #{conn.id}"))
        else:
            # Ensure it is active
            if conn.status != 'active':
                conn.status = 'active'
                conn.save(update_fields=['status'])
                self.stdout.write(self.style.SUCCESS(f"Reactivated SelfConnection #{conn.id}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"SelfConnection #{conn.id} already exists and is active"))
