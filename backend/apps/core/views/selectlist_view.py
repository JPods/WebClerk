"""
SelectListCatalogView — every select list, for the Select Lists page.

A field's list is its model's own, in the model definition (config.selectlists.<field>,
services/select_lists.py); this view indexes those across Settings with the Setting id and
path so the page can show and open them. There is no other tier (readme 105, 2026-11-05: the
record-level and profile-level lists had no stored use and are gone).
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.core.models import Setting

def _extract_options(config: dict) -> list:
    """Walk a Setting config and extract all select list arrays.

    Canonical path: config.selectlists.<field> = [{value, label}]
    """
    entries = []
    if not isinstance(config, dict):
        return entries

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

    return entries


class SelectListCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """A flat index of every select list a Setting holds (config.selectlists.<field>)."""
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
