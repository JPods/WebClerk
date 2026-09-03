"""
alice_clean_backups — Remove expired merge backups from contact config.

Backups are created when contacts are merged via the Contact Paste tool.
They're a safety net for accidental merges — 24 hours is enough to notice
a mistake. After that, Alice cleans them up.

Usage:
    python manage.py alice_clean_backups              # clean backups > 24h old
    python manage.py alice_clean_backups --hours 48   # custom age
    python manage.py alice_clean_backups --dry-run    # preview only
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Remove expired merge backups from contact config (default: 24h)'

    def add_arguments(self, parser):
        parser.add_argument('--hours', type=int, default=24, help='Max backup age in hours')
        parser.add_argument('--dry-run', action='store_true', help='Preview without deleting')

    def handle(self, *args, **options):
        from apps.ai_assistant.services.contact_parser import clean_merge_backups

        result = clean_merge_backups(
            max_age_hours=options['hours'],
            dry_run=options['dry_run'],
        )

        prefix = '[DRY RUN] ' if options['dry_run'] else ''
        self.stdout.write(self.style.SUCCESS(
            f'{prefix}Merge backups: {result["cleaned"]} cleaned, {result["skipped"]} still fresh'
        ))
