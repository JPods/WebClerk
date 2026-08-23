"""Create a session Document record — process memory for each work session.

A session document is created at session start and updated during the session.
It captures what was done, what was decided, what's open. Alice reads these
to build cumulative understanding of how the system evolved and why.

The session document is a living record during the session, not a post-hoc
summary. Actions, decisions, and scars are appended as they happen.

Usage:
    # Start a session (creates the document)
    python manage.py seed_session_document --start

    # Append an entry during the session
    python manage.py seed_session_document --append "Fixed MCP server paths"

    # Close the session (sets status to complete)
    python manage.py seed_session_document --close

Or via wcapi from React/Claude Code:
    saveRecord({
        model_name: 'document',
        purpose: 'session',
        name: 'Session 2026-08-06',
        ...
    })
"""
import datetime
from django.core.management.base import BaseCommand
from apps.docs.models.document import Document


def today_ida():
    return f"session-{datetime.date.today().isoformat()}"


class Command(BaseCommand):
    help = 'Create or update a session Document record'

    def add_arguments(self, parser):
        parser.add_argument('--start', action='store_true', help='Start a new session document')
        parser.add_argument('--append', type=str, help='Append an entry to today\'s session')
        parser.add_argument('--close', action='store_true', help='Close today\'s session')

    def handle(self, *args, **options):
        ida = today_ida()
        today = datetime.date.today().isoformat()

        if options['start']:
            obj, created = Document.objects.update_or_create(
                ida=ida,
                defaults={
                    'name': f'Session {today}',
                    'purpose': 'session',
                    'status': 'active',
                    'description': f'Work session {today}',
                    'body': f'# Session {today}\n\n## Actions\n\n## Decisions\n\n## Open\n\n',
                },
            )
            verb = 'Created' if created else 'Reopened'
            self.stdout.write(self.style.SUCCESS(f'{verb} session document: {ida}'))

        elif options['append']:
            try:
                obj = Document.objects.get(ida=ida)
            except Document.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'No session for {today}. Run --start first.'))
                return
            ts = datetime.datetime.now().strftime('%H:%M')
            entry = f'- [{ts}] {options["append"]}\n'
            obj.body = (obj.body or '') + entry
            obj.save(update_fields=['body'])
            self.stdout.write(f'  Appended: {entry.strip()}')

        elif options['close']:
            try:
                obj = Document.objects.get(ida=ida)
            except Document.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'No session for {today}.'))
                return
            obj.status = 'complete'
            obj.save(update_fields=['status'])
            self.stdout.write(self.style.SUCCESS(f'Closed session: {ida}'))
