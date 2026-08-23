"""Pack the canonical settings bundle from the database.

Exports all system-scope Setting records as settings-bundle.json.
DB is master — this file is the git snapshot for offline/fallback use.

Usage:
    python manage.py pack_settings_bundle                    # write to settings-bundle.json
    python manage.py pack_settings_bundle --output /tmp/sb.json  # custom path
    python manage.py pack_settings_bundle --dry-run          # show what would be exported
    python manage.py pack_settings_bundle --validate         # pack + run health check
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.core.models.setting import Setting


class Command(BaseCommand):
    help = 'Export all active Settings as a canonical bundle (DB → git snapshot)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output', type=str, default='settings-bundle.json',
            help='Output file path (default: settings-bundle.json in project root)',
        )
        parser.add_argument('--dry-run', action='store_true', help='Show count and purposes without writing')
        parser.add_argument('--validate', action='store_true', help='Run health check after packing')

    def handle(self, *args, **options):
        records = []
        for s in Setting.objects.filter(is_active=True).order_by('purpose', 'parent_model', 'id'):
            rec = {
                'uuid': str(s.uuid) if s.uuid else '',
                'ida': s.ida or '',
                'name': s.name or '',
                'scope': s.scope or 'system',
                'purpose': s.purpose or '',
                'parent_model': s.parent_model or '',
                'explanation': getattr(s, 'explanation', '') or '',
                'paths': getattr(s, 'paths', {}) or {},
                'config': s.config or {},
                'metadata': s.metadata or {},
                'prefs': s.prefs or {},
                'refs': s.refs or {},
            }
            # Ensure UUID exists — every bundled record must be UUID-addressable
            if not rec['uuid']:
                self.stderr.write(self.style.WARNING(
                    f"  SKIP id={s.id} ida={s.ida} — no UUID (cannot be merge-controlled)"
                ))
                continue
            records.append(rec)

        bundle = {
            'version': '1.0',
            'source': 'pack_settings_bundle',
            'dt_exported': datetime.now(timezone.utc).isoformat(),
            'record_count': len(records),
            'settings': records,
        }

        # Group by purpose for summary
        purposes = {}
        for r in records:
            p = r['purpose'] or 'None'
            purposes[p] = purposes.get(p, 0) + 1

        self.stdout.write(f"\nSettings bundle: {len(records)} records")
        for p, count in sorted(purposes.items()):
            self.stdout.write(f"  {p}: {count}")

        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS('\n(dry run — nothing written)'))
            return

        output_path = Path(options['output'])
        with open(output_path, 'w') as f:
            json.dump(bundle, f, indent=2, ensure_ascii=False)

        size_kb = output_path.stat().st_size / 1024
        self.stdout.write(self.style.SUCCESS(
            f"\nWritten to {output_path} ({size_kb:.0f} KB)"
        ))

        if options['validate']:
            from apps.core.services.settings_health import check_settings_health
            report = check_settings_health()
            if report['healthy']:
                self.stdout.write(self.style.SUCCESS(f"Health check: PASSED ({report['summary']})"))
            else:
                self.stdout.write(self.style.ERROR(f"Health check: FAILED ({report['summary']})"))
                for m in report['missing']:
                    self.stdout.write(self.style.ERROR(f"  MISSING: {m['type']}"))
                for c in report['corrupt'][:5]:
                    self.stdout.write(self.style.ERROR(f"  CORRUPT: {c['ida']} — {', '.join(c['issues'])}"))
