"""
Migrate workbench_fields Settings from config.list/detail/views
to config.db.list/detail/views.

Converts bare string field names to DbFieldSpec dicts.
Preserves existing FieldSpec dicts (width, align, etc.).
Idempotent — skips records already migrated.

Usage:
  ./manage.py migrate_db_layouts          # dry run
  ./manage.py migrate_db_layouts --apply  # write changes
"""
from django.core.management.base import BaseCommand
from apps.core.models import Setting


def to_field_spec(item):
    """Convert a string or dict to a DbFieldSpec-compatible dict."""
    if isinstance(item, str):
        return {'field': item, 'visible': True}
    if isinstance(item, dict) and 'field' in item:
        # Already a FieldSpec — normalize
        spec = {'field': item['field'], 'visible': item.get('visible', True)}
        for key in ('width', 'min_width', 'max_width', 'align', 'format',
                     'wrap', 'frozen', 'summary', 'alice_note', 'type_hint'):
            if key in item and item[key] is not None:
                spec[key] = item[key]
        # Handle camelCase from React (typeHint, minWidth, maxWidth)
        if 'typeHint' in item:
            spec['type_hint'] = item['typeHint']
        if 'minWidth' in item:
            spec['min_width'] = item['minWidth']
        if 'maxWidth' in item:
            spec['max_width'] = item['maxWidth']
        return spec
    # Unknown shape — skip
    return None


def migrate_views(views):
    """Convert named views to new structure."""
    migrated = []
    for v in views:
        if not isinstance(v, dict) or 'name' not in v:
            continue
        nv = {'name': v['name']}
        for key in ('list', 'detail'):
            items = v.get(key, [])
            nv[key] = [s for s in (to_field_spec(i) for i in items) if s]
        # panel and card don't exist yet — empty
        nv['panel'] = []
        nv['card'] = []
        migrated.append(nv)
    return migrated


class Command(BaseCommand):
    help = 'Migrate workbench_fields config.list/detail/views → config.db.*'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Write changes (default is dry run)')

    def handle(self, *args, **options):
        apply = options['apply']
        qs = Setting.objects.filter(purpose='wc:workbench_fields')
        total = qs.count()
        migrated = 0
        skipped = 0
        errors = 0

        for s in qs:
            cfg = s.config or {}

            # Already migrated?
            if 'db' in cfg and isinstance(cfg['db'], dict):
                skipped += 1
                continue

            old_list = cfg.get('list', [])
            old_detail = cfg.get('detail', [])
            old_views = cfg.get('views', [])

            # Convert
            new_list = [sp for sp in (to_field_spec(i) for i in old_list) if sp]
            new_detail = [sp for sp in (to_field_spec(i) for i in old_detail) if sp]
            new_views = migrate_views(old_views)

            db = {
                'list': new_list,
                'detail': new_detail,
                'panel': [],
                'card': [],
                'views': new_views,
            }

            # Build new config: remove old keys, add db
            new_cfg = {k: v for k, v in cfg.items()
                       if k not in ('list', 'detail', 'views')}
            new_cfg['db'] = db

            self.stdout.write(
                f'  {s.parent_model}: '
                f'list {len(old_list)}→{len(new_list)}, '
                f'detail {len(old_detail)}→{len(new_detail)}, '
                f'views {len(old_views)}→{len(new_views)}'
            )

            if apply:
                try:
                    s.config = new_cfg
                    s.save(update_fields=['config'])
                    migrated += 1
                except Exception as e:
                    self.stderr.write(f'  ERROR {s.parent_model}: {e}')
                    errors += 1
            else:
                migrated += 1

        mode = 'APPLIED' if apply else 'DRY RUN'
        self.stdout.write(self.style.SUCCESS(
            f'\n{mode}: {total} total, {migrated} migrated, '
            f'{skipped} already done, {errors} errors'
        ))
