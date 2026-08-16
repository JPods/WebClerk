"""
migrate_named_layouts — Convert config.layout from flat arrays to named layout dicts.

Converts the old structure:
  config.layout.list[]         — flat array of field specs
  config.layout.detail[]|{}    — field specs OR DynamicDetail sections
  config.layout.views[]        — separate named view snapshots
  config.layout.panel[]        — panel field specs
  config.layout.card[]         — card field specs

To the new structure:
  config.layout.active         — which named layout is selected per type
  config.layout.list.default   — {detail, ui, columns: [...]}
  config.layout.detail.default — {list, ui, fields: [...]}
  config.layout.ui.default     — {list, detail, ...DynamicDetail}
  config.layout.panel[]        — unchanged
  config.layout.card[]         — unchanged

Rules:
  - Old layout.list (array) → layout.list.default.columns
  - Old layout.detail (array of field specs) → layout.detail.default.fields
  - Old layout.detail (DynamicDetail dict) → layout.ui.default (sections preserved)
  - Old layout.views entries → additional named entries under list/detail
  - layout.views is removed
  - panel and card stay as flat arrays
  - Idempotent — skips records already in new format

Usage:
  ./manage.py migrate_named_layouts              # dry run
  ./manage.py migrate_named_layouts --apply      # write changes
  ./manage.py migrate_named_layouts --model action  # one model only
"""
from django.core.management.base import BaseCommand
from apps.core.models import Setting


def is_new_format(layout):
    """Check if layout is already in the new named-dict format."""
    if not layout:
        return False
    list_val = layout.get('list')
    # New format: layout.list is a dict of named layouts
    # Old format: layout.list is an array of field specs
    return isinstance(list_val, dict)


def normalize_field_spec(spec):
    """Ensure a field spec is a dict, not a bare string."""
    if isinstance(spec, str):
        return {'field': spec, 'visible': True}
    return spec


def migrate_layout(layout):
    """Convert a single layout from old format to new format.

    Returns (new_layout, changes_description).
    """
    if not layout:
        return {
            'active': {'list': 'default', 'column': 'default', 'dynamic': 'default', 'display': 'default'},
            'list': {'default': {'dynamic': 'default', 'display': 'default', 'columns': []}},
            'column': {'default': {'dynamic': 'default', 'display': 'default', 'columns': []}},
            'dynamic': {'default': {'list': 'default', 'display': 'default'}},
            'display': {'default': {'list': 'default', 'dynamic': 'default'}},
            'panel': [],
            'card': [],
        }, 'empty layout → defaults'

    old_list = layout.get('list', [])
    old_detail = layout.get('detail', [])
    old_views = layout.get('views', [])
    old_panel = layout.get('panel', [])
    old_card = layout.get('card', [])
    old_related = layout.get('related', [])

    changes = []

    # --- Build layout.list ---
    new_list = {}
    if isinstance(old_list, list) and old_list:
        new_list['default'] = {
            'dynamic': 'default',
            'display': 'default',
            'columns': [normalize_field_spec(s) for s in old_list],
        }
        changes.append(f'list: {len(old_list)} fields → default')
    else:
        new_list['default'] = {'dynamic': 'default', 'display': 'default', 'columns': []}

    # --- Build layout.column (panel grid) ---
    new_column = {}
    if isinstance(old_panel, list) and old_panel:
        new_column['default'] = {
            'dynamic': 'default',
            'display': 'default',
            'columns': [normalize_field_spec(s) for s in old_panel],
        }
        changes.append(f'panel → column.default: {len(old_panel)} fields')
    else:
        new_column['default'] = {'dynamic': 'default', 'display': 'default', 'columns': []}

    # --- Build layout.dynamic (DynamicDetail sections) ---
    new_dynamic = {}
    if isinstance(old_detail, dict) and old_detail:
        # Old detail was DynamicDetail sections → dynamic layout
        dyn_entry = {
            'list': 'default',
            'display': 'default',
        }
        for k, v in old_detail.items():
            dyn_entry[k] = v
        new_dynamic['default'] = dyn_entry
        changes.append(f'detail (DynamicDetail) → dynamic.default')
    else:
        new_dynamic['default'] = {'list': 'default', 'display': 'default'}

    # --- Build layout.display (JSON-driven detail pages) ---
    new_display = {}
    new_display['default'] = {'list': 'default', 'dynamic': 'default'}

    # --- Migrate views into named list entries ---
    for view in old_views:
        if not isinstance(view, dict):
            continue
        name = view.get('name', '')
        if not name:
            continue

        view_list = view.get('list', [])
        if isinstance(view_list, list) and view_list:
            new_list[name] = {
                'dynamic': 'default',
                'display': 'default',
                'columns': [normalize_field_spec(s) for s in view_list],
            }

        changes.append(f'view "{name}" → named entries')

    # --- Assemble new layout ---
    new_layout = {
        'active': {'list': 'default', 'column': 'default', 'dynamic': 'default', 'display': 'default'},
        'list': new_list,
        'column': new_column,
        'dynamic': new_dynamic,
        'display': new_display,
        'panel': old_panel,
        'card': old_card,
    }
    if old_related:
        new_layout['related'] = old_related

    return new_layout, '; '.join(changes) if changes else 'no data to migrate'


class Command(BaseCommand):
    help = 'Convert config.layout from flat arrays to named layout dicts'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Write changes (default is dry run)')
        parser.add_argument('--model', type=str, help='Migrate one model only')

    def handle(self, *args, **options):
        apply = options['apply']
        model_filter = options.get('model')

        qs = Setting.objects.filter(purpose='wc:model', is_active=True)
        if model_filter:
            qs = qs.filter(parent_model=model_filter)

        total = qs.count()
        migrated = 0
        skipped = 0
        errors = 0

        self.stdout.write(f'\n{"APPLYING" if apply else "DRY RUN"} — {total} wc:model settings\n')

        for setting in qs.order_by('parent_model'):
            config = setting.config or {}
            layout = config.get('layout', {})

            if is_new_format(layout):
                skipped += 1
                self.stdout.write(f'  SKIP  {setting.parent_model} (id={setting.id}) — already migrated')
                continue

            try:
                new_layout, desc = migrate_layout(layout)

                if apply:
                    config['layout'] = new_layout
                    setting.config = config
                    setting.save(update_fields=['config'])

                migrated += 1
                prefix = 'WRITE' if apply else 'WOULD'
                self.stdout.write(f'  {prefix} {setting.parent_model} (id={setting.id}) — {desc}')

                # Show named layout counts
                nl = len(new_layout.get('list', {}))
                nd = len(new_layout.get('detail', {}))
                nu = len(new_layout.get('ui', {}))
                self.stdout.write(f'         list: {nl} named, detail: {nd} named, ui: {nu} named')

            except Exception as e:
                errors += 1
                self.stderr.write(f'  ERROR {setting.parent_model} (id={setting.id}) — {e}')

        self.stdout.write(f'\nDone: {migrated} migrated, {skipped} skipped, {errors} errors\n')
