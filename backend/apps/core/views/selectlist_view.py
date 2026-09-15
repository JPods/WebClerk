"""
SelectListCatalogView — scans all Settings for select list arrays.

Returns a flat index of every options/choices array found in Settings,
plus the Setting ID and path so the frontend can edit in place.

Three-tier inheritance (most specific wins):
  1. Model-level:    Setting(parent_model=X, purpose='wc:model').config.selectlists
  2. Category-level: record.config.selectlist_profile → Setting.config.selectlists
  3. Record-level:   record.config.selectlists (inline on the record itself)

Use ?model_name=&record_id= to get resolved lists for a specific record.
"""
import logging
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.core.models import Setting

logger = logging.getLogger(__name__)


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


def resolve_selectlists(model_name, record=None):
    """Three-tier select list resolution.

    Returns: {field: {options: [...], source: 'model'|'profile'|'record', source_detail: str}}

    Tier 1 (model):    Setting(parent_model=model_name).config.selectlists
    Tier 2 (profile):  record.config.selectlist_profile → Setting.config.selectlists
    Tier 3 (record):   record.config.selectlists (inline)

    Most specific wins per field.
    """
    merged = {}

    # Tier 1: model-level Setting selectlists
    model_settings = Setting.objects.filter(
        parent_model=model_name, is_active=True,
    ).only('id', 'ida', 'config')
    for s in model_settings:
        cfg = s.config if isinstance(s.config, dict) else {}
        sl = cfg.get('selectlists')
        if isinstance(sl, dict):
            for field, opts in sl.items():
                if isinstance(opts, list) and len(opts) > 0:
                    merged[field] = {
                        'options': opts,
                        'source': 'model',
                        'source_detail': f'Setting {s.ida} (id={s.id})',
                    }

    if not record:
        return merged

    # Get record config
    record_config = getattr(record, 'config', None)
    if not isinstance(record_config, dict):
        return merged

    # Tier 2: selectlist_profile → another Setting
    profile = record_config.get('selectlist_profile')
    if isinstance(profile, dict) and profile.get('id'):
        try:
            profile_setting = Setting.objects.only('id', 'ida', 'config').get(
                id=profile['id'], is_active=True,
            )
            pcfg = profile_setting.config if isinstance(profile_setting.config, dict) else {}
            sl = pcfg.get('selectlists')
            if isinstance(sl, dict):
                for field, opts in sl.items():
                    if isinstance(opts, list) and len(opts) > 0:
                        merged[field] = {
                            'options': opts,
                            'source': 'profile',
                            'source_detail': f'Setting {profile_setting.ida} (id={profile_setting.id})',
                        }
        except Setting.DoesNotExist:
            logger.warning("selectlist_profile points to missing Setting id=%s", profile.get('id'))

    # Tier 3: record's own inline selectlists
    record_sl = record_config.get('selectlists')
    if isinstance(record_sl, dict):
        for field, opts in record_sl.items():
            if isinstance(opts, list) and len(opts) > 0:
                merged[field] = {
                    'options': opts,
                    'source': 'record',
                    'source_detail': f'record.config.selectlists.{field}',
                }

    return merged


class SelectListCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return select lists — flat catalog or resolved for a specific record.

        Without params: flat index of all select lists across Settings.
        With ?model_name=&record_id=: three-tier resolved lists for that record.
        """
        model_name = request.query_params.get('model_name')
        record_id = request.query_params.get('record_id')

        # ── Resolved mode: three-tier for a specific record ──
        if model_name and record_id:
            return self._resolve_for_record(model_name, record_id)

        # ── Catalog mode: flat index of all selectlists ──
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

    def _resolve_for_record(self, model_name, record_id):
        """Resolve three-tier selectlists for a specific record."""
        from apps.core.constants.model_registry import get_model_meta

        meta = get_model_meta(model_name)
        if not meta:
            return Response({'error': f'Unknown model: {model_name}'}, status=404)

        try:
            record = meta.model_class.objects.only('id', 'config').get(id=record_id)
        except meta.model_class.DoesNotExist:
            return Response({'error': f'{model_name} {record_id} not found'}, status=404)

        merged = resolve_selectlists(model_name, record)

        return Response({
            'model_name': model_name,
            'record_id': int(record_id),
            'selectlists': {
                field: info for field, info in merged.items()
            },
            'total': len(merged),
        })
