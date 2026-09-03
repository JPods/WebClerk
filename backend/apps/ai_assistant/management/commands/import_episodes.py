"""
Import Episode records from a JSON file exported by export_episodes.

Usage:
    python manage.py import_episodes --file /tmp/ep.json
    python manage.py import_episodes --file /tmp/ep.json --dry-run
    python manage.py import_episodes --file /tmp/ep.json --review-status raw
"""
import json

from django.core.management.base import BaseCommand

from apps.sync.services.episode_bundle import ingest_episodes


class Command(BaseCommand):
    help = 'Import Episode records from a JSON bundle file (upsert via ingest_episodes).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file', '-f', required=True,
            help='Path to the JSON file exported by export_episodes.',
        )
        parser.add_argument(
            '--review-status', default='approved',
            help='Review status for new episodes (default: approved).',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Parse and validate without writing to the database.',
        )

    def handle(self, *args, **options):
        file_path = options['file']
        review_status = options['review_status']
        dry_run = options['dry_run']

        with open(file_path, 'r') as f:
            payload = json.load(f)

        episodes = payload.get('episodes', [])
        self.stderr.write(f'Read {len(episodes)} episodes from {file_path}\n')

        if dry_run:
            valid = sum(1 for ep in episodes if ep.get('episode_id'))
            invalid = len(episodes) - valid
            self.stderr.write(
                f'Dry run: {valid} valid episodes, {invalid} missing episode_id\n'
            )
            return

        result = ingest_episodes(episodes, review_status=review_status)
        self.stderr.write(
            f'Import complete: '
            f'{result["created"]} created, '
            f'{result["updated"]} updated, '
            f'{result["skipped"]} skipped\n'
        )
