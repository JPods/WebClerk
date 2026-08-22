"""Pack the init bundle — Settings + Reports for a new database.

Every new WC3 database starts with this file. It contains all wc:model
Settings (layouts for list, detail, form) and all Report records
(forms, print templates, search presets, utilities).

Usage:
    python manage.py pack_init_bundle                             # write to init-bundle.json
    python manage.py pack_init_bundle --output /tmp/init.json     # custom path
    python manage.py pack_init_bundle --dry-run                   # show what would be exported
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.core.models.setting import Setting


class Command(BaseCommand):
    help = 'Export Settings + Reports as init-bundle.json (seed for new databases)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output', type=str, default='init-bundle.json',
            help='Output file path (default: init-bundle.json in project root)',
        )
        parser.add_argument('--dry-run', action='store_true', help='Show counts without writing')

    def _serialize_setting(self, s):
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
            'metadata': {**(s.metadata or {}), 'foundational': True},
            'prefs': s.prefs or {},
            'refs': s.refs or {},
        }
        if not rec['uuid']:
            return None
        return rec

    def _serialize_report(self, r):
        if not r.uuid:
            return None
        return {
            'uuid': str(r.uuid),
            'ida': r.ida or '',
            'name': r.name or '',
            'description': r.description or '',
            'model_name': r.model_name or '',
            'record_id': r.record_id or '',
            'output_type': r.output_type or '',
            'category': r.category or '',
            'role_required': r.role_required or '',
            'sort_order': r.sort_order or 0,
            'explanation': getattr(r, 'explanation', '') or '',
            'paths': getattr(r, 'paths', {}) or {},
            'config': r.config or {},
            'metadata': {**(r.metadata or {}), 'foundational': True},
            'prefs': r.prefs or {},
            'refs': r.refs or {},
            'editor_type': r.editor_type or '',
            'content': r.content or '',
            'script_before': r.script_before or '',
            'script_during': r.script_during or '',
            'script_after': r.script_after or '',
        }

    def handle(self, *args, **options):
        from django.apps import apps
        Report = None
        for ac in apps.get_app_configs():
            for m in ac.get_models():
                if m.__name__ == 'Report':
                    Report = m
                    break

        # --- Settings ---
        settings_list = []
        skipped_s = 0
        for s in Setting.objects.filter(is_active=True).order_by('purpose', 'parent_model'):
            rec = self._serialize_setting(s)
            if rec:
                settings_list.append(rec)
            else:
                skipped_s += 1

        # --- Reports ---
        reports_list = []
        skipped_r = 0
        if Report:
            for r in Report.objects.filter(is_active=True).order_by('model_name', 'category', 'name'):
                rec = self._serialize_report(r)
                if rec:
                    reports_list.append(rec)
                else:
                    skipped_r += 1

        bundle = {
            'version': '1.0',
            'source': 'pack_init_bundle',
            'dt_exported': datetime.now(timezone.utc).isoformat(),
            'settings_count': len(settings_list),
            'reports_count': len(reports_list),
            'settings': settings_list,
            'reports': reports_list,
        }

        # Summary
        purposes = {}
        for r in settings_list:
            p = r['purpose'] or 'None'
            purposes[p] = purposes.get(p, 0) + 1

        categories = {}
        for r in reports_list:
            c = f"{r['model_name']}/{r['category']}" if r['model_name'] else r['category']
            categories[c] = categories.get(c, 0) + 1

        self.stdout.write(f"\n=== Init Bundle ===")
        self.stdout.write(f"\nSettings: {len(settings_list)} records")
        for p, count in sorted(purposes.items()):
            self.stdout.write(f"  {p}: {count}")
        if skipped_s:
            self.stdout.write(self.style.WARNING(f"  ({skipped_s} skipped — no UUID)"))

        self.stdout.write(f"\nReports: {len(reports_list)} records")
        for c, count in sorted(categories.items()):
            self.stdout.write(f"  {c}: {count}")
        if skipped_r:
            self.stdout.write(self.style.WARNING(f"  ({skipped_r} skipped — no UUID)"))

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
