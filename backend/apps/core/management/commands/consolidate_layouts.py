"""
consolidate_layouts — Move config.columns into config.layout for all wc:model Settings.

Consolidates the buried config.columns.db.{list,panel,card,views} structure
into config.layout.{list,panel,card,views}, alongside the existing
config.layout detail sections (DynamicDetail).

Rules:
  - Strips 'id' and 'uuid' fields from list/panel columns (plumbing, not human)
  - Ensures 'ida' leads the list if present
  - Preserves existing config.layout (DynamicDetail sections) as layout.detail
  - Removes config.columns after migration
  - Idempotent — skips records already migrated

Usage:
  ./manage.py consolidate_layouts              # dry run
  ./manage.py consolidate_layouts --apply      # write changes
  ./manage.py consolidate_layouts --model action  # one model only
"""
from django.core.management.base import BaseCommand
from apps.core.models import Setting


PLUMBING_FIELDS = {'id', 'uuid'}


def clean_field_list(specs):
    """Remove plumbing fields, ensure ida leads."""
    if not specs:
        return []

    cleaned = []
    ida_spec = None

    for spec in specs:
        if isinstance(spec, str):
            field_name = spec
            spec = {'field': spec, 'visible': True}
        elif isinstance(spec, dict):
            field_name = spec.get('field', '')
        else:
            continue

        # Strip plumbing
        if field_name in PLUMBING_FIELDS:
            continue

        # Capture ida separately so we can put it first
        if field_name == 'ida':
            ida_spec = spec
            continue

        cleaned.append(spec)

    # ida leads
    if ida_spec:
        cleaned.insert(0, ida_spec)

    return cleaned


class Command(BaseCommand):
    help = 'Consolidate config.columns into config.layout for wc:model Settings'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Write changes (default is dry run)')
        parser.add_argument('--model', type=str, default=None,
                            help='Process one model only (by Setting name or model key)')

    def handle(self, *args, **options):
        apply = options['apply']
        model_filter = options.get('model')

        qs = Setting.objects.filter(purpose='wc:model', is_active=True, is_deleted=False)

        if model_filter:
            # Try exact name match first, then partial
            filtered = qs.filter(name__icontains=model_filter)
            if not filtered.exists():
                self.stderr.write(f'No wc:model Setting found matching "{model_filter}"')
                return
            qs = filtered

        total = qs.count()
        migrated = 0
        skipped = 0
        errors = 0

        for s in qs:
            cfg = s.config or {}
            old_columns = cfg.get('columns', {})
            old_layout = cfg.get('layout', {})

            # Already migrated? layout has list/panel/card keys
            if isinstance(old_layout, dict) and 'list' in old_layout and 'columns' not in cfg:
                skipped += 1
                continue

            # Source: columns.db.* (the buried structure) or columns.list/detail (flat)
            db_cols = {}
            if isinstance(old_columns, dict):
                db_cols = old_columns.get('db', old_columns)

            # Extract and clean
            old_list = db_cols.get('list', []) if isinstance(db_cols, dict) else []
            old_panel = db_cols.get('panel', []) if isinstance(db_cols, dict) else []
            old_card = db_cols.get('card', []) if isinstance(db_cols, dict) else []
            old_views = db_cols.get('views', []) if isinstance(db_cols, dict) else []

            new_list = clean_field_list(old_list)
            new_panel = clean_field_list(old_panel)
            new_card = clean_field_list(old_card)

            # Preserve DynamicDetail sections as layout.detail
            detail_sections = {}
            if isinstance(old_layout, dict):
                # Current layout has model, family, sections, edit_rules
                if 'sections' in old_layout or 'model' in old_layout:
                    detail_sections = old_layout

            # Build new layout
            new_layout = {
                'list': new_list,
                'panel': new_panel,
                'card': new_card,
                'views': old_views,
            }
            if detail_sections:
                new_layout['detail'] = detail_sections

            # Report
            self.stdout.write(
                f'  {s.name}: '
                f'list {len(old_list)}→{len(new_list)}, '
                f'panel {len(old_panel)}→{len(new_panel)}, '
                f'card {len(old_card)}→{len(new_card)}, '
                f'views {len(old_views)}, '
                f'detail {"yes" if detail_sections else "no"}'
            )

            if apply:
                try:
                    cfg['layout'] = new_layout
                    # Remove old columns key
                    cfg.pop('columns', None)
                    s.config = cfg
                    s.save(update_fields=['config'])
                    migrated += 1
                except Exception as e:
                    self.stderr.write(f'  ERROR {s.name}: {e}')
                    errors += 1
            else:
                migrated += 1

        mode = 'APPLIED' if apply else 'DRY RUN'
        self.stdout.write(self.style.SUCCESS(
            f'\n{mode}: {total} total, {migrated} would migrate, '
            f'{skipped} already done, {errors} errors'
        ))
