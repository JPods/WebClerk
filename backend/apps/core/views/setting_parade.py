"""
Setting Parade — guided walk through Setting records that shape the UI.

Spec: readmes/architecture/setting-parade.md

Three endpoints:
  GET  /wcapi/_setting_parade_manifest/   — all Settings grouped by what they control
  GET  /wcapi/_setting_parade_preview/    — structured preview for one Setting
  POST /wcapi/_setting_parade_feedback/   — save feedback on a Setting
"""
import logging
from datetime import datetime, timezone

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import Setting

logger = logging.getLogger(__name__)

# ── Purpose → group mapping ──────────────────────────────────────────

PURPOSE_GROUPS = [
    {
        'name': 'Field Behaviors',
        'description': 'How fields render — widget type, labels, readonly',
        'filter': lambda s: s.purpose == 'wc:model',
    },
    {
        'name': 'Select Lists',
        'description': 'Dropdown options per field — three-tier inheritance',
        'filter': lambda s: _has_selectlists(s),
    },
    {
        'name': 'List Layouts',
        'description': 'Column order, widths, visibility in list views',
        'filter': lambda s: s.purpose in ('wc:list_column_config', 'wc:workbench_fields'),
    },
    {
        'name': 'Defaults',
        'description': 'Default field values for new records',
        'filter': lambda s: _is_defaults(s),
    },
    {
        'name': 'Field Access',
        'description': 'Role-based field visibility and edit rules',
        'filter': lambda s: s.purpose == 'wc:field_access',
    },
]


def _has_selectlists(s):
    """Check if a Setting has config.selectlists with at least one entry."""
    cfg = s.config if isinstance(s.config, dict) else {}
    sl = cfg.get('selectlists')
    return isinstance(sl, dict) and len(sl) > 0


def _is_defaults(s):
    """Check if a Setting's name ends with _defaults."""
    name = (s.name or '').lower()
    ida = (s.ida or '').lower()
    return name.endswith('_defaults') or ida.endswith('_defaults')


def _get_record_refs_count(s):
    """Count records whose config references this Setting (e.g. selectlist_profile)."""
    if not s.parent_model:
        return 0
    try:
        from apps.core.constants.model_registry import import_model
        model_cls = import_model(s.parent_model)
        if model_cls is None:
            return 0
        return model_cls.objects.filter(
            config__selectlist_profile__id=s.id,
            is_active=True,
        ).count()
    except Exception:
        return 0


def _summarize_setting(s):
    """Build a summary dict for a Setting's config contents."""
    cfg = s.config if isinstance(s.config, dict) else {}
    prefs = s.prefs if isinstance(getattr(s, 'prefs', None), dict) else {}
    summary = {}

    # Behaviors
    behaviors = cfg.get('behaviors', {})
    if isinstance(behaviors, dict) and behaviors:
        summary['behavior_count'] = len(behaviors)
        select_fields = [
            f for f, b in behaviors.items()
            if isinstance(b, dict) and b.get('type') == 'select'
        ]
        if select_fields:
            summary['select_fields'] = select_fields

    # Selectlists
    selectlists = cfg.get('selectlists', {})
    if isinstance(selectlists, dict) and selectlists:
        summary['selectlist_count'] = len(selectlists)

    # Record refs — how many records point to this Setting
    record_refs = _get_record_refs_count(s)
    summary['record_refs'] = record_refs

    return summary


def _get_feedback(s):
    """Extract parade feedback from Setting.prefs."""
    prefs = s.prefs if isinstance(getattr(s, 'prefs', None), dict) else {}
    return prefs.get('parade_feedback')


# ── Manifest ─────────────────────────────────────────────────────────

class SettingParadeManifestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return all Settings grouped by what they control."""
        settings = list(
            Setting.objects.filter(is_active=True)
            .order_by('parent_model', 'purpose', 'name')
        )

        grouped_ids = set()
        groups = []

        for group_def in PURPOSE_GROUPS:
            entries = []
            for s in settings:
                if s.id in grouped_ids:
                    continue
                if group_def['filter'](s):
                    entries.append({
                        'id': s.id,
                        'ida': s.ida,
                        'name': s.name or '',
                        'parent_model': s.parent_model or '',
                        'purpose': s.purpose or '',
                        'summary': _summarize_setting(s),
                        'feedback': _get_feedback(s),
                    })
                    grouped_ids.add(s.id)
            if entries:
                groups.append({
                    'name': group_def['name'],
                    'description': group_def['description'],
                    'settings': entries,
                    'count': len(entries),
                })

        # Catch-all for ungrouped
        other = []
        for s in settings:
            if s.id not in grouped_ids:
                other.append({
                    'id': s.id,
                    'ida': s.ida,
                    'name': s.name or '',
                    'parent_model': s.parent_model or '',
                    'purpose': s.purpose or '',
                    'summary': _summarize_setting(s),
                    'feedback': _get_feedback(s),
                })
        if other:
            groups.append({
                'name': 'Other',
                'description': 'Settings not in the categories above',
                'settings': other,
                'count': len(other),
            })

        reviewed = sum(
            1 for g in groups for s in g['settings'] if s['feedback']
        )

        return Response({
            'groups': groups,
            'total_settings': len(settings),
            'reviewed_count': reviewed,
        })


# ── Preview ──────────────────────────────────────────────────────────

class SettingParadePreviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return structured preview data for a single Setting."""
        setting_id = request.query_params.get('setting_id')
        if not setting_id:
            return Response({'error': 'setting_id required'}, status=400)

        try:
            s = Setting.objects.get(id=setting_id, is_active=True)
        except Setting.DoesNotExist:
            return Response({'error': f'Setting {setting_id} not found'}, status=404)

        cfg = s.config if isinstance(s.config, dict) else {}
        prefs = s.prefs if isinstance(getattr(s, 'prefs', None), dict) else {}

        preview = {
            'id': s.id,
            'ida': s.ida,
            'name': s.name or '',
            'parent_model': s.parent_model or '',
            'purpose': s.purpose or '',
            'explanation': s.explanation or '',
            'scope': s.scope,
        }

        # ── Field Behaviors (wc:model) ──
        # Table of field → widget type → label → options
        behaviors = cfg.get('behaviors', {})
        if isinstance(behaviors, dict) and behaviors:
            rows = []
            for field_name, spec in behaviors.items():
                if not isinstance(spec, dict):
                    continue
                rows.append({
                    'field': field_name,
                    'widget_type': spec.get('type', ''),
                    'label': spec.get('label', field_name),
                    'readonly': spec.get('readonly', False),
                    'precision': spec.get('precision'),
                    'selectlist_key': spec.get('selectlist_key', ''),
                    'options': {k: v for k, v in spec.items()
                                if k not in ('type', 'label', 'readonly', 'precision', 'selectlist_key')},
                })
            preview['behaviors'] = rows

        # ── Select Lists ──
        # Options table with value/label columns
        selectlists = cfg.get('selectlists', {})
        if isinstance(selectlists, dict) and selectlists:
            sl_preview = {}
            for field_name, options in selectlists.items():
                if isinstance(options, list):
                    sl_preview[field_name] = {
                        'option_count': len(options),
                        'options': options,
                    }
                elif isinstance(options, dict):
                    sl_preview[field_name] = {
                        'option_count': len(options),
                        'options': options,
                    }
            preview['selectlists'] = sl_preview

        # Count records that reference this Setting via selectlist_profile
        profile_refs = _get_record_refs_count(s)
        if profile_refs:
            preview['profile_ref_count'] = profile_refs

        # ── Layouts ──
        # Column preview: field names in order with widths
        for key in ('list', 'detail'):
            layout = cfg.get(key, [])
            if isinstance(layout, list) and layout:
                preview[f'{key}_layout'] = layout

        # Field groups
        field_groups = cfg.get('field_groups', [])
        if isinstance(field_groups, list) and field_groups:
            preview['field_groups'] = field_groups

        # ── Defaults ──
        # Key/value table of default field values
        defaults = prefs.get('defaults', {}) if isinstance(prefs, dict) else {}
        if isinstance(defaults, dict) and defaults:
            preview['defaults'] = defaults

        # Feedback
        preview['feedback'] = _get_feedback(s)

        return Response(preview)


# ── Feedback ─────────────────────────────────────────────────────────

class SettingParadeFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Save parade feedback on a Setting record."""
        setting_id = request.data.get('setting_id')
        choice = request.data.get('feedback')
        notes = request.data.get('notes', '')

        if not setting_id:
            return Response({'error': 'setting_id required'}, status=400)

        valid_choices = ('understood', 'needs_work', 'dont_understand')
        if choice not in valid_choices:
            return Response({
                'error': f'feedback must be one of: {", ".join(valid_choices)}',
            }, status=400)

        try:
            s = Setting.objects.get(id=setting_id, is_active=True)
        except Setting.DoesNotExist:
            return Response({'error': f'Setting {setting_id} not found'}, status=404)

        # Store feedback in prefs.parade_feedback
        prefs = s.prefs if isinstance(getattr(s, 'prefs', None), dict) else {}
        prefs['parade_feedback'] = {
            'choice': choice,
            'notes': notes,
            'reviewed_by': request.user.username if request.user else '',
            'reviewed_at': datetime.now(timezone.utc).isoformat(),
        }
        s.prefs = prefs
        s.save(update_fields=['prefs', 'dt_modified', 'version'])

        return Response({'ok': True, 'setting_id': s.id, 'feedback': choice})
