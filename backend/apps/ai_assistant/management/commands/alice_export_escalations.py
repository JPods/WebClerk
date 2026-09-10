"""
alice_export_escalations — Export escalation observations for sync.

Every WCHQ escalation produces an AliceObservation(category='escalation').
This command exports them for Allie's nightly reflection.

Usage:
    python manage.py alice_export_escalations --since 2026-09-01T00:00:00Z --output /path/to/escalations.json
    python manage.py alice_export_escalations --days 7 --output /path/to/escalations.json
"""
import json
from datetime import datetime, timezone, timedelta
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Export WCHQ escalation observations for Allie reflection'

    def add_arguments(self, parser):
        parser.add_argument('--since', default='', help='ISO datetime cutoff (UTC)')
        parser.add_argument('--days', type=int, default=0, help='Export last N days')
        parser.add_argument('--output', required=True, help='Output JSON file path')

    def handle(self, *args, **options):
        from django.apps import apps as dj_apps

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
            'type': 'alice_escalations',
            'version': '1.0',
            'exported_at': datetime.now(timezone.utc).isoformat(),
            'since': since_dt.isoformat(),
            'escalations': [],
        }

        try:
            AliceObservation = dj_apps.get_model('ai_assistant', 'AliceObservation')
            escalations = AliceObservation.objects.filter(
                dt_created__gte=since_ms,
                is_active=True,
            ).filter(
                # Filter for escalation-related observations
                # category stored in config.category or metadata.category
                config__category='escalation',
            ).values(
                'id', 'ida', 'uuid', 'config', 'metadata', 'status',
                'dt_created', 'dt_modified',
            )

            export['escalations'] = [
                {k: (str(v) if k == 'uuid' else v) for k, v in esc.items()}
                for esc in escalations
            ]
        except Exception as e:
            # If category filter doesn't work on JSONField, try broader query
            self.stdout.write(self.style.WARNING(f"Escalation query: {e}"))
            try:
                AliceObservation = dj_apps.get_model('ai_assistant', 'AliceObservation')
                all_obs = AliceObservation.objects.filter(
                    dt_created__gte=since_ms, is_active=True,
                ).values('id', 'ida', 'uuid', 'config', 'metadata', 'status',
                         'dt_created', 'dt_modified')

                for obs in all_obs:
                    cfg = obs.get('config') or {}
                    meta = obs.get('metadata') or {}
                    cat = cfg.get('category', '') or meta.get('category', '')
                    if cat == 'escalation':
                        obs['uuid'] = str(obs['uuid'])
                        export['escalations'].append(obs)
            except Exception as e2:
                self.stdout.write(self.style.WARNING(f"Fallback query: {e2}"))

        with open(output_path, 'w') as f:
            json.dump(export, f, indent=2, default=str)

        self.stdout.write(self.style.SUCCESS(
            f"Exported {len(export['escalations'])} escalations since "
            f"{since_dt.strftime('%Y-%m-%d')} → {output_path}"
        ))
