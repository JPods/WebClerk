"""
Export Episode records to JSON for transfer to another WC3 instance.

Usage:
    python manage.py export_episodes                          # stdout
    python manage.py export_episodes --output /tmp/ep.json    # file
"""
import json
import sys

from django.core.management.base import BaseCommand

from apps.ai_assistant.models import Episode


EXPORT_FIELDS = [
    'episode_id', 'uuid', 'episode_type', 'domain', 'title',
    'narrative', 'principle', 'actors', 'outcome', 'severity',
    'related_episodes', 'tags', 'source_ref', 'recall_count',
    'dt_start', 'dt_end', 'dt_created', 'source_instance',
    'review_status', 'quality_score',
]


class Command(BaseCommand):
    help = 'Export active Episode records to JSON (episode bundle format).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output', '-o',
            help='Output file path. Defaults to stdout.',
        )

    def handle(self, *args, **options):
        qs = Episode.objects.filter(is_active=True).order_by('dt_created')
        episodes = []

        for ep in qs.values(*EXPORT_FIELDS):
            # Convert UUIDs to strings for JSON serialization
            if ep.get('uuid'):
                ep['uuid'] = str(ep['uuid'])
            if ep.get('source_instance'):
                ep['source_instance'] = str(ep['source_instance'])
            episodes.append(ep)

        payload = {
            'type': 'episode_bundle',
            'version': '1.0',
            'count': len(episodes),
            'episodes': episodes,
        }

        output = json.dumps(payload, indent=2, default=str)
        out_path = options.get('output')

        if out_path:
            with open(out_path, 'w') as f:
                f.write(output)
                f.write('\n')
            self.stderr.write(f'Exported {len(episodes)} episodes to {out_path}\n')
        else:
            self.stdout.write(output)
            self.stderr.write(f'Exported {len(episodes)} episodes to stdout\n')
