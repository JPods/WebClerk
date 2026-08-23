"""
SelectListCatalogView — scans all Settings for select list arrays.

Returns a flat index of every options/choices array found in Settings,
plus the Setting ID and path so the frontend can edit in place.

Four config paths scanned:
  - config.lists.<name>.choices          (purpose=wc:admin)
  - config.behaviors.<field>.options     (purpose=wc:model)
  - config.field_behaviors.<field>.options (purpose=wc:field_access)
  - config.select_lists.<name>.options   (purpose=wc:company_profile)
"""
import json
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.core.models import Setting


def _extract_options(config: dict) -> list:
    """Walk a Setting config and extract all select list arrays.

    Primary path: config.selectlists.<field> = [{value, label}]
    Legacy fallback paths (read-only, for backward compat):
      - config.behaviors.<field>.options
      - config.field_behaviors.<field>.options
      - config.lists.<name>.choices
      - config.select_lists.<name>.options
    """
    entries = []
    if not isinstance(config, dict):
        return entries

    seen_fields = set()

    # Primary: config.selectlists.<field> — canonical location
    selectlists = config.get('selectlists')
    if isinstance(selectlists, dict):
        for field, opts in selectlists.items():
            if isinstance(opts, list) and len(opts) > 0:
                entries.append({
                    'field': field,
                    'path': f'selectlists.{field}',
                    'options': opts,
                    'count': len(opts),
                })
                seen_fields.add(field)

    # Legacy fallback: config.behaviors.<field>.options
    behaviors = config.get('behaviors')
    if isinstance(behaviors, dict):
        for field, spec in behaviors.items():
            if field in seen_fields:
                continue
            if isinstance(spec, dict):
                options = spec.get('options')
                if isinstance(options, list) and len(options) > 0:
                    entries.append({
                        'field': field,
                        'path': f'behaviors.{field}.options',
                        'options': options,
                        'count': len(options),
                    })
                    seen_fields.add(field)

    # Legacy fallback: config.field_behaviors.<field>.options
    fb = config.get('field_behaviors')
    if isinstance(fb, dict):
        for field, spec in fb.items():
            if field in seen_fields:
                continue
            if isinstance(spec, dict):
                options = spec.get('options')
                if isinstance(options, list) and len(options) > 0:
                    entries.append({
                        'field': field,
                        'path': f'field_behaviors.{field}.options',
                        'options': options,
                        'count': len(options),
                    })
                    seen_fields.add(field)

    # Legacy fallback: config.lists.<name>.choices
    lists = config.get('lists')
    if isinstance(lists, dict):
        for name, lst in lists.items():
            if name in seen_fields:
                continue
            if isinstance(lst, dict):
                choices = lst.get('choices')
                if isinstance(choices, list) and len(choices) > 0:
                    entries.append({
                        'field': name,
                        'path': f'lists.{name}.choices',
                        'options': choices,
                        'count': len(choices),
                    })
                    seen_fields.add(name)

    # Legacy fallback: config.select_lists.<name>.options
    sl = config.get('select_lists')
    if isinstance(sl, dict):
        for name, spec in sl.items():
            if name in seen_fields:
                continue
            if isinstance(spec, dict):
                options = spec.get('options')
                if isinstance(options, list) and len(options) > 0:
                    entries.append({
                        'field': name,
                        'path': f'select_lists.{name}.options',
                        'options': options,
                        'count': len(options),
                    })
                    seen_fields.add(name)

    return entries


class SelectListCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return flat index of all select lists found in Settings."""
        rows = []
        for s in Setting.objects.filter(is_active=True).only('id', 'ida', 'name', 'parent_model', 'purpose', 'config'):
            if not s.config or not isinstance(s.config, dict):
                continue
            entries = _extract_options(s.config)
            for entry in entries:
                rows.append({
                    'field': entry['field'],
                    'path': entry['path'],
                    'count': entry['count'],
                    'options': entry['options'],
                    'setting_id': s.id,
                    'setting_ida': s.ida,
                    'setting_name': s.name or '',
                    'setting_parent_model': s.parent_model or '',
                    'setting_purpose': s.purpose or '',
                })

        # Sort by field name
        rows.sort(key=lambda r: (r['field'].lower(), r['setting_ida']))

        # Build "like" groups — same field name across different settings
        field_groups = {}
        for r in rows:
            field_groups.setdefault(r['field'], []).append(r['setting_ida'])

        for r in rows:
            siblings = field_groups.get(r['field'], [])
            r['shared_count'] = len(siblings)

        return Response({
            'rows': rows,
            'total': len(rows),
            'unique_fields': len(field_groups),
        })
