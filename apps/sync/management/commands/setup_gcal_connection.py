from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.sync.models.connection import Connection


class Command(BaseCommand):
    help = "Create or update a Google Calendar Connection configured for local-only OAuth (env or file-based secrets, token storage on disk)."

    def add_arguments(self, parser):
        parser.add_argument('--name', required=True, help='Human-friendly name for the connection (e.g., Google Calendar - Primary)')
        parser.add_argument('--env-prefix', default='', help='Environment variable prefix (e.g., GCAL_PRIMARY). Will read ${PREFIX}_CLIENT_ID/SECRET/REDIRECT_URI at runtime.')
        parser.add_argument('--credentials-file', default='', help='Path to a local JSON with {client_id, client_secret, redirect_uri}. Relative paths resolved from BASE_DIR.')
        parser.add_argument('--token-storage', default='file', choices=['file', 'db'], help='Where to store OAuth tokens. Use file to keep tokens off the database.')
        parser.add_argument('--token-path', default='', help='Custom path for token file (default: .local/google_tokens_<id>.json). Relative paths resolved from BASE_DIR.')
        parser.add_argument('--purpose', default='google_calendar', help='Optional purpose tag.')

    @transaction.atomic
    def handle(self, *args, **options):
        name = options['name']
        env_prefix = options['env_prefix'].strip()
        credentials_file = options['credentials_file'].strip()
        token_storage = options['token_storage']
        token_path = options['token_path'].strip()
        purpose = options['purpose']

        if not env_prefix and not credentials_file:
            self.stdout.write(self.style.WARNING('No --env-prefix or --credentials-file provided. You can still set them later on the Connection.'))

        conn, created = Connection.objects.get_or_create(
            name=name,
            defaults={
                'type': 'google_calendar',
                'config': {},
                'purpose': purpose,
                'status': '',
            },
        )

        cfg = conn.config or {}
        # Only store pointers, not secrets
        if env_prefix:
            cfg['env_prefix'] = env_prefix
        if credentials_file:
            cfg['credentials_file'] = credentials_file
        if token_path:
            cfg['token_path'] = token_path
        cfg['token_storage'] = token_storage

        conn.config = cfg
        if created:
            conn.status = 'new'
        conn.save()

        self.stdout.write(self.style.SUCCESS(f"Connection {conn.id} {'created' if created else 'updated'}: {conn.name}"))
        self.stdout.write('Next steps:')
        self.stdout.write('  1) Ensure your local env has the values set if using --env-prefix (e.g., PREFIX_CLIENT_ID/SECRET/REDIRECT_URI).')
        self.stdout.write('  2) Or provide a local JSON credentials file with {client_id, client_secret, redirect_uri}.')
        self.stdout.write('  3) Start the OAuth flow at /sync/google/calendar/start?connection_id=<ID> while logged in as staff/admin.')
