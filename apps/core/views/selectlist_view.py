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
    """Walk a Setting config and extract all options/choices arrays with their paths."""
    entries = []
    if not isinstance(config, dict):
        return entries

    # Pattern 1: config.lists.<name>.choices (wc:admin)
    lists = config.get('lists')
    if isinstance(lists, dict):
        for name, lst in lists.items():
            if isinstance(lst, dict):
                choices = lst.get('choices')
                if isinstance(choices, list):
                    entries.append({
                        'field': name,
                        'path': f'lists.{name}.choices',
                        'options': choices,
                        'count': len(choices),
                    })

    # Pattern 2: config.behaviors.<field>.options (wc:model)
    behaviors = config.get('behaviors')
    if isinstance(behaviors, dict):
        for field, spec in behaviors.items():
            if isinstance(spec, dict):
                options = spec.get('options')
                if isinstance(options, list) and len(options) > 0:
                    entries.append({
                        'field': field,
                        'path': f'behaviors.{field}.options',
                        'options': options,
                        'count': len(options),
                    })

    # Pattern 3: config.field_behaviors.<field>.options (wc:field_access)
    fb = config.get('field_behaviors')
    if isinstance(fb, dict):
        for field, spec in fb.items():
            if isinstance(spec, dict):
                options = spec.get('options')
                if isinstance(options, list) and len(options) > 0:
                    entries.append({
                        'field': field,
                        'path': f'field_behaviors.{field}.options',
                        'options': options,
                        'count': len(options),
                    })

    # Pattern 4: config.select_lists.<name>.options (wc:company_profile)
    sl = config.get('select_lists')
    if isinstance(sl, dict):
        for name, spec in sl.items():
            if isinstance(spec, dict):
                options = spec.get('options')
                if isinstance(options, list) and len(options) > 0:
                    entries.append({
                        'field': name,
                        'path': f'select_lists.{name}.options',
                        'options': options,
                        'count': len(options),
                    })

    return entries


class SelectListCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return flat index of all select lists found in Settings."""
        rows = []
        for s in Setting.objects.filter(is_active=True).only('id', 'ida', 'purpose', 'config'):
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
