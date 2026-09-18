"""
selectlist_bundle — Export/import select lists as JSON bundles.

Round-trip workflow:
    1. Export:  python manage.py selectlist_bundle export
    2. Edit the JSON in the JSON editor
    3. Import:  python manage.py selectlist_bundle import

Export scans all Settings for selectlists (canonical + legacy paths),
normalizes to [{value, label}], and writes a single JSON file.

Import reads that JSON and writes back to config.selectlists on each
matched Setting. Matching is by ida (primary) or id (fallback).

The JSON lives in DATA_DIR/bundles/selectlist/ by default.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core.models.setting import Setting

logger = logging.getLogger(__name__)

DEFAULT_FILENAME = 'selectlists.json'


def _bundle_dir() -> Path:
    path = Path(settings.DATA_DIR) / 'bundles' / 'selectlist'
    path.mkdir(parents=True, exist_ok=True)
    return path


def _extract_all_selectlists(setting):
    """Extract selectlists from a Setting, checking canonical + legacy paths.

    Returns dict of {field: [{value, label}]} with canonical winning over legacy.
    """
    cfg = setting.config if isinstance(setting.config, dict) else {}
    merged = {}

    # Legacy: config.lists.<name>.choices (ida-114 style)
    lists = cfg.get('lists')
    if isinstance(lists, dict):
        for name, v in lists.items():
            if isinstance(v, dict):
                choices = v.get('choices', [])
                if isinstance(choices, list) and choices:
                    # choices may be plain strings or {value, label} dicts
                    normalized = []
                    for c in choices:
                        if isinstance(c, dict):
                            normalized.append({
                                'value': c.get('value', ''),
                                'label': c.get('label', c.get('value', '')),
                            })
                        elif isinstance(c, str):
                            normalized.append({'value': c, 'label': c})
                    if normalized:
                        merged[name] = normalized

    # Legacy: config.behaviors.<field>.options
    behaviors = cfg.get('behaviors')
    if isinstance(behaviors, dict):
        for field, v in behaviors.items():
            if isinstance(v, dict):
                opts = v.get('options')
                if isinstance(opts, list) and opts:
                    normalized = [
                        {'value': o.get('value', ''), 'label': o.get('label', o.get('value', ''))}
                        for o in opts if isinstance(o, dict)
                    ]
                    if normalized:
                        merged[field] = normalized

    # Legacy: config.select_lists.<field> (underscore variant)
    select_lists = cfg.get('select_lists')
    if isinstance(select_lists, dict):
        for field, v in select_lists.items():
            if isinstance(v, list) and v:
                normalized = [
                    {'value': o.get('value', ''), 'label': o.get('label', o.get('value', ''))}
                    for o in v if isinstance(o, dict)
                ]
                if normalized:
                    merged[field] = normalized
            elif isinstance(v, dict):
                # seed_select_lists format: {choices: [...], label: ...}
                choices = v.get('choices', [])
                if isinstance(choices, list) and choices:
                    normalized = []
                    for c in choices:
                        if isinstance(c, dict):
                            normalized.append({
                                'value': c.get('value', ''),
                                'label': c.get('label', c.get('value', '')),
                            })
                        elif isinstance(c, str):
                            normalized.append({'value': c, 'label': c})
                    if normalized:
                        merged[field] = normalized

    # Canonical: config.selectlists.<field> — wins over everything
    selectlists = cfg.get('selectlists')
    if isinstance(selectlists, dict):
        for field, opts in selectlists.items():
            if isinstance(opts, list) and opts:
                normalized = [
                    {'value': o.get('value', ''), 'label': o.get('label', o.get('value', ''))}
                    for o in opts if isinstance(o, dict)
                ]
                if normalized:
                    merged[field] = normalized

    return merged


def export_selectlists(stdout, style, filepath=None):
    """Export all selectlists to a JSON bundle file."""
    if filepath is None:
        filepath = _bundle_dir() / DEFAULT_FILENAME

    entries = []
    qs = Setting.objects.filter(is_active=True).only(
        'id', 'ida', 'name', 'parent_model', 'purpose', 'config',
    ).order_by('ida')

    for s in qs:
        selectlists = _extract_all_selectlists(s)
        if not selectlists:
            continue

        total_opts = sum(len(v) for v in selectlists.values())
        entries.append({
            'id': s.id,
            'ida': s.ida,
            'name': s.name or '',
            'parent_model': s.parent_model or '',
            'purpose': s.purpose or '',
            'selectlists': dict(sorted(selectlists.items())),
        })
        stdout.write(
            f'  {s.ida:<35} {len(selectlists):>3} fields  {total_opts:>4} options'
        )

    bundle = {
        '_meta': {
            'format': 'wc3_selectlist_bundle',
            'version': 1,
            'exported_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'total_settings': len(entries),
            'total_fields': sum(len(e['selectlists']) for e in entries),
            'total_options': sum(
                sum(len(opts) for opts in e['selectlists'].values())
                for e in entries
            ),
        },
        'settings': entries,
    }

    Path(filepath).write_text(json.dumps(bundle, indent=2, default=str), encoding='utf-8')
    stdout.write(style.SUCCESS(
        f'\nExported {len(entries)} settings, '
        f'{bundle["_meta"]["total_fields"]} fields, '
        f'{bundle["_meta"]["total_options"]} options → {filepath}'
    ))
    return filepath


def import_selectlists(stdout, style, filepath=None, dry_run=False):
    """Import selectlists from a JSON bundle file into Settings.

    Writes to the canonical config.selectlists path. Matches Settings by ida.
    """
    if filepath is None:
        filepath = _bundle_dir() / DEFAULT_FILENAME

    filepath = Path(filepath)
    if not filepath.exists():
        stdout.write(style.ERROR(f'File not found: {filepath}'))
        stdout.write('Run "selectlist_bundle export" first to create the file.')
        return

    bundle = json.loads(filepath.read_text(encoding='utf-8'))

    meta = bundle.get('_meta', {})
    if meta.get('format') != 'wc3_selectlist_bundle':
        stdout.write(style.ERROR('Not a selectlist bundle (wrong format in _meta)'))
        return

    tag = '[DRY RUN] ' if dry_run else ''
    updated = skipped = not_found = 0

    for entry in bundle.get('settings', []):
        ida = entry.get('ida')
        entry_id = entry.get('id')
        selectlists = entry.get('selectlists', {})

        if not ida:
            stdout.write(style.WARNING(f'  {tag}Skipping entry with no ida'))
            skipped += 1
            continue

        # Match by ida (primary), fall back to id
        try:
            setting = Setting.objects.get(ida=ida, is_active=True)
        except Setting.DoesNotExist:
            if entry_id:
                try:
                    setting = Setting.objects.get(id=entry_id, is_active=True)
                except Setting.DoesNotExist:
                    setting = None
            else:
                setting = None

        if not setting:
            stdout.write(style.WARNING(f'  {tag}Not found: {ida} (id={entry_id})'))
            not_found += 1
            continue

        # Compare current vs incoming
        cfg = setting.config if isinstance(setting.config, dict) else {}
        current = cfg.get('selectlists', {})

        if current == selectlists:
            stdout.write(f'  {tag}Unchanged: {ida}')
            skipped += 1
            continue

        field_count = len(selectlists)
        opt_count = sum(len(v) for v in selectlists.values())

        if not dry_run:
            cfg['selectlists'] = selectlists
            setting.config = cfg
            setting._setting_update_authorized = True
            setting.save(update_fields=['config'])

        stdout.write(f'  {tag}Updated: {ida} — {field_count} fields, {opt_count} options')
        updated += 1

    stdout.write(style.SUCCESS(
        f'\n{tag}Import: {updated} updated, {skipped} unchanged, {not_found} not found'
    ))


class Command(BaseCommand):
    help = 'Export/import select lists as JSON bundles for editing'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['export', 'import'],
                            help='export = Settings → JSON; import = JSON → Settings')
        parser.add_argument('--file', type=str, default=None,
                            help=f'JSON file path (default: DATA_DIR/bundles/selectlist/{DEFAULT_FILENAME})')
        parser.add_argument('--dry-run', action='store_true',
                            help='Preview import without writing')

    def handle(self, *args, **options):
        action = options['action']
        filepath = options.get('file')
        dry_run = options.get('dry_run', False)

        if action == 'export':
            export_selectlists(self.stdout, self.style, filepath)
        elif action == 'import':
            import_selectlists(self.stdout, self.style, filepath, dry_run)
