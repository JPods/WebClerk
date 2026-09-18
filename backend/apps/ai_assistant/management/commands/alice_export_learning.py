"""
alice_export_learning — Export Alice's episodes and observations for sync.

Usage:
    python manage.py alice_export_learning --since 2026-09-01T00:00:00Z --output /path/to/episodes.json
    python manage.py alice_export_learning --days 7 --output /path/to/episodes.json
"""
import json
from datetime import datetime, timezone, timedelta
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Export Alice episodes and observations for Andi↔Local sync'

    def add_arguments(self, parser):
        parser.add_argument('--since', default='', help='ISO datetime cutoff (UTC)')
        parser.add_argument('--days', type=int, default=0, help='Export last N days (alternative to --since)')
        parser.add_argument('--output', required=True, help='Output JSON file path')

    def handle(self, *args, **options):
        from django.apps import apps as dj_apps

        # Determine cutoff
        if options['since']:
            since_str = options['since'].replace('Z', '+00:00')
            since_dt = datetime.fromisoformat(since_str)
        elif options['days']:
            since_dt = datetime.now(timezone.utc) - timedelta(days=options['days'])
        else:
            since_dt = datetime.now(timezone.utc) - timedelta(days=1)

        since_ms = int(since_dt.timestamp() * 1000)
        output_path = options['output']

        export = {
            'type': 'alice_learning',
            'version': '1.0',
            'exported_at': datetime.now(timezone.utc).isoformat(),
            'since': since_dt.isoformat(),
            'episodes': [],
            'observations': [],
            'standards': [],
        }

        # Export episodes
        try:
            Episode = dj_apps.get_model('ai_assistant', 'Episode')
            episodes = Episode.objects.filter(
                dt_created__gte=since_ms, is_active=True,
            ).values(
                'id', 'ida', 'uuid', 'config', 'metadata', 'status',
                'dt_created', 'dt_modified',
            )
            export['episodes'] = [
                {k: (str(v) if k == 'uuid' else v) for k, v in ep.items()}
                for ep in episodes
            ]
            self.stdout.write(f"  Episodes: {len(export['episodes'])}")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Episodes: skipped ({e})"))

        # Export observations
        try:
            AliceObservation = dj_apps.get_model('ai_assistant', 'AliceObservation')
            observations = AliceObservation.objects.filter(
                dt_created__gte=since_ms, is_active=True,
            ).values(
                'id', 'ida', 'uuid', 'config', 'metadata', 'status',
                'dt_created', 'dt_modified',
            )
            export['observations'] = [
                {k: (str(v) if k == 'uuid' else v) for k, v in obs.items()}
                for obs in observations
            ]
            self.stdout.write(f"  Observations: {len(export['observations'])}")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Observations: skipped ({e})"))

        # Export promoted standards
        try:
            AliceStandard = dj_apps.get_model('ai_assistant', 'AliceStandard')
            standards = AliceStandard.objects.filter(
                dt_modified__gte=since_ms, is_active=True,
            ).values(
                'id', 'ida', 'uuid', 'config', 'metadata', 'status',
                'dt_created', 'dt_modified',
            )
            export['standards'] = [
                {k: (str(v) if k == 'uuid' else v) for k, v in std.items()}
                for std in standards
            ]
            self.stdout.write(f"  Standards: {len(export['standards'])}")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Standards: skipped ({e})"))

        # Write output
        with open(output_path, 'w') as f:
            json.dump(export, f, indent=2, default=str)

        total = len(export['episodes']) + len(export['observations']) + len(export['standards'])
        self.stdout.write(self.style.SUCCESS(
            f"Exported {total} records since {since_dt.strftime('%Y-%m-%d')} → {output_path}"
        ))
