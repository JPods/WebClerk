"""
Seed the ai_episode table from Allie's episodes table (allie database).

Usage:
    python manage.py seed_episodes           # upsert all 196 episodes
    python manage.py seed_episodes --dry-run # preview without writing
"""
import os
import uuid

import psycopg2
import psycopg2.extras
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.ai_assistant.models import Episode


ALLIE_DB = {
    'dbname': 'allie',
    'user': os.getlogin(),
    'host': 'localhost',
}

FIELD_MAP = [
    'episode_id', 'episode_type', 'domain', 'title', 'narrative',
    'principle', 'actors', 'outcome', 'severity', 'related_episodes',
    'tags', 'source_ref', 'recall_count', 'dt_start', 'dt_end',
    'dt_created', 'metadata',
]


def _safe_uuid(val):
    """Parse a UUID string, return None if missing or invalid."""
    if not val:
        return None
    try:
        return uuid.UUID(str(val))
    except (ValueError, AttributeError):
        return None


class Command(BaseCommand):
    help = 'Seed ai_episode from Allie episodes table (allie database)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Preview counts without writing to database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # --- read from allie database ---
        conn = psycopg2.connect(**ALLIE_DB)
        conn.set_client_encoding('UTF8')
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM episodes ORDER BY dt_created')
        rows = cur.fetchall()
        cur.close()
        conn.close()

        self.stdout.write(f'Read {len(rows)} episodes from allie database')

        created = updated = skipped = 0
        now_ms = int(timezone.now().timestamp() * 1000)

        for row in rows:
            eid = row.get('episode_id')
            if not eid:
                skipped += 1
                continue

            defaults = {}
            for field in FIELD_MAP:
                if field == 'episode_id':
                    continue  # lookup key, not a default
                val = row.get(field)

                # bigint fields: coerce None → 0
                if field in ('dt_start', 'dt_end', 'dt_created', 'recall_count'):
                    val = val or 0

                # json fields: coerce None → appropriate default
                if field in ('actors', 'related_episodes', 'tags'):
                    val = val if val is not None else []
                if field == 'metadata':
                    val = val if val is not None else {}

                # text fields: coerce None → ''
                if field in ('narrative', 'principle', 'source_ref'):
                    val = val or ''

                defaults[field] = val

            # review fields — these are approved production episodes
            defaults['review_status'] = 'approved'
            defaults['reviewed_by'] = 'seed'
            defaults['dt_reviewed'] = now_ms
            defaults['source_instance'] = None  # allie has no WC3 instance UUID

            if dry_run:
                exists = Episode.objects.filter(episode_id=eid).exists()
                if exists:
                    updated += 1
                else:
                    created += 1
                continue

            _, was_created = Episode.objects.update_or_create(
                episode_id=eid,
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        label = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'{label}Done — created: {created}, updated: {updated}, skipped: {skipped}'
        ))
