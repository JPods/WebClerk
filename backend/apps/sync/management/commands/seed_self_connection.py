"""Seed the SelfConnection — internal Connection for tools that post bundles
to their own WC3 instance (JSON Tree, Matrix Builder, etc.).

Usage: ./manage.py seed_self_connection
"""
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
                    'key': 'self-connection',
                    'description': 'Internal connection for tools posting bundles to this instance',
                },
                'comment': 'Auto-created. Used by JSON Tree, Matrix Builder, and other local tools.',
            },
        )
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
