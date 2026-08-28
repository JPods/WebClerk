"""Unpack the init bundle — Settings + Reports into a new database.

UUID controls merge: existing records updated (baseline merge),
missing records created. User customizations are never overwritten.

Usage:
    python manage.py unpack_init_bundle                           # from init-bundle.json
    python manage.py unpack_init_bundle --input /tmp/init.json    # custom path
    python manage.py unpack_init_bundle --dry-run                 # show what would change
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand


def _deep_merge_baseline(existing: dict, incoming: dict) -> dict:
    """Add missing keys from incoming; never replace existing values."""
    merged = dict(existing)
    for key, value in incoming.items():
        if key not in merged:
            merged[key] = value
        elif isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge_baseline(merged[key], value)
    return merged


class Command(BaseCommand):
    help = 'Import Settings + Reports from init-bundle.json (seed a new database)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--input', type=str, default='init-bundle.json',
            help='Input file path (default: init-bundle.json in project root)',
        )
        parser.add_argument('--dry-run', action='store_true', help='Show what would change without writing')

    def _import_settings(self, records, dry_run):
        from apps.core.services.setting_bootstrap import import_settings_bundle
        if dry_run:
            from apps.core.models.setting import Setting
            created, updated = 0, 0
            for rec in records:
                uuid_val = rec.get('uuid')
                if not uuid_val:
                    continue
                if Setting.objects.filter(uuid=uuid_val).exists():
                    updated += 1
                else:
                    created += 1
            return created, updated, []
        # Init bundle has authority over foundational records
        result = import_settings_bundle(records, force_foundational=True)
        return result['created'], result['updated'], result['errors']

    def _import_reports(self, records, dry_run):
        from django.apps import apps
        Report = None
        for ac in apps.get_app_configs():
            for m in ac.get_models():
                if m.__name__ == 'Report':
                    Report = m
                    break
        if not Report:
            return 0, 0, ['Report model not found']

        created, updated, errors = 0, 0, []
        scalar_fields = (
            'name', 'description', 'model_name', 'record_id', 'output_type',
            'category', 'role_required', 'sort_order', 'explanation',
            'editor_type', 'content', 'script_before', 'script_during', 'script_after',
        )
        json_fields = ('config', 'metadata', 'refs', 'paths')

        for rec in records:
            uuid_val = rec.get('uuid')
            if not uuid_val:
                errors.append(f"Report missing uuid: name={rec.get('name', '?')}")
                continue
            existing = Report.objects.filter(uuid=uuid_val).first()
            if dry_run:
                if existing:
                    updated += 1
                else:
                    created += 1
                continue
            if existing:
                # Init bundle has full authority — update all fields
                for field in scalar_fields:
                    if field in rec:
                        setattr(existing, field, rec[field])
                for field in json_fields:
                    if field in rec:
                        current = getattr(existing, field, None) or {}
                        incoming = rec[field] or {}
                        if isinstance(current, dict) and isinstance(incoming, dict):
                            setattr(existing, field, _deep_merge_baseline(current, incoming))
                        elif not current:
                            setattr(existing, field, incoming)
                # Ensure foundational flag is set
                meta = existing.metadata or {}
                meta['foundational'] = True
                existing.metadata = meta
                existing.save()
                updated += 1
            else:
                kwargs = {'uuid': uuid_val, 'ida': rec.get('ida', '')}
                for field in scalar_fields:
                    if field in rec:
                        kwargs[field] = rec[field]
                for field in json_fields:
                    kwargs[field] = rec.get(field, {})
                # Ensure foundational flag on new records
                meta = kwargs.get('metadata', {}) or {}
                meta['foundational'] = True
                kwargs['metadata'] = meta
                kwargs['prefs'] = rec.get('prefs', {})
                Report.objects.create(**kwargs)
                created += 1
        return created, updated, errors

    def handle(self, *args, **options):
        input_path = Path(options['input'])
        if not input_path.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {input_path}"))
            return

        with open(input_path) as f:
            bundle = json.load(f)

        settings_recs = bundle.get('settings', [])
        reports_recs = bundle.get('reports', [])
        dry_run = options['dry_run']

        self.stdout.write(f"\nInit bundle: {len(settings_recs)} settings, {len(reports_recs)} reports")
        self.stdout.write(f"Source: {bundle.get('source', '?')} — {bundle.get('dt_exported', '?')}")

        s_created, s_updated, s_errors = self._import_settings(settings_recs, dry_run)
        r_created, r_updated, r_errors = self._import_reports(reports_recs, dry_run)

        label = 'Dry run' if dry_run else 'Result'
        self.stdout.write(f"\n{label}:")
        self.stdout.write(f"  Settings — created: {s_created}, updated: {s_updated}")
        self.stdout.write(f"  Reports  — created: {r_created}, updated: {r_updated}")

        all_errors = s_errors + r_errors
        if all_errors:
            for e in all_errors:
                self.stderr.write(self.style.ERROR(f"  ERROR: {e}"))
        else:
            self.stdout.write(self.style.SUCCESS('  No errors.'))
