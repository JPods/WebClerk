"""
SettingParadeView — guided walk through Setting records that shape the UI.

Same pattern as parade_preview_view.py (manifest + preview + feedback)
but for configuration instead of print forms.

Users learn PJPV by seeing what each Setting does.
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
        'filter': lambda s: s.purpose and 'defaults' in (s.purpose or ''),
    },
    {
        'name': 'Field Access',
        'description': 'Role-based field visibility and edit rules',
        'filter': lambda s: s.purpose == 'wc:field_access',
    },
    {
        'name': 'Other',
        'description': 'Settings not in the categories above',
        'filter': None,  # catch-all — assigned to ungrouped settings
    },
]


def _has_selectlists(s):
    """Check if a Setting has config.selectlists with at least one entry."""
    cfg = s.config if isinstance(s.config, dict) else {}
    sl = cfg.get('selectlists')
    return isinstance(sl, dict) and len(sl) > 0


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
        summary['selectlist_fields'] = list(selectlists.keys())

    # Field groups
    field_groups = cfg.get('field_groups', [])
    if isinstance(field_groups, list) and field_groups:
        summary['field_group_count'] = len(field_groups)

    # Defaults
    defaults = prefs.get('defaults', {}) if isinstance(prefs, dict) else {}
    if isinstance(defaults, dict) and defaults:
        summary['default_count'] = len(defaults)

    # Layout fields
    for key in ('list', 'detail'):
        layout = cfg.get(key, [])
        if isinstance(layout, list) and layout:
            summary[f'{key}_field_count'] = len(layout)

    return summary


def _get_feedback(s):
    """Extract parade feedback from Setting.prefs."""
    prefs = s.prefs if isinstance(getattr(s, 'prefs', None), dict) else {}
    return prefs.get('parade_feedback')


class SettingParadeManifestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return grouped Settings with summaries for the parade."""
        settings = list(Setting.objects.filter(is_active=True).order_by('parent_model', 'purpose', 'name'))

        grouped_ids = set()
        groups = []

        for group_def in PURPOSE_GROUPS:
            if group_def['filter'] is None:
                continue
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
                        'explanation': s.explanation or '',
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
                    'explanation': s.explanation or '',
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

        # Behaviors — field → {type, label, precision, readonly, options, selectlist_key}
        behaviors = cfg.get('behaviors', {})
        if isinstance(behaviors, dict) and behaviors:
            preview['behaviors'] = behaviors

        # Selectlists — field → [{value, label}]
        selectlists = cfg.get('selectlists', {})
        if isinstance(selectlists, dict) and selectlists:
            preview['selectlists'] = selectlists

        # Count records that point to this Setting via selectlist_profile
        try:
            from apps.core.constants.model_registry import get_model_meta
            if s.parent_model:
                meta = get_model_meta(s.parent_model)
                if meta:
                    model_cls = meta.model_class
                    # Count records with config.selectlist_profile.id = this setting
                    profile_refs = model_cls.objects.filter(
                        config__selectlist_profile__id=s.id,
                        is_active=True,
                    ).count()
                    if profile_refs:
                        preview['profile_ref_count'] = profile_refs
        except Exception:
            pass

        # Field groups
        field_groups = cfg.get('field_groups', [])
        if isinstance(field_groups, list) and field_groups:
            preview['field_groups'] = field_groups

        # Layout
        for key in ('list', 'detail'):
            layout = cfg.get(key, [])
            if isinstance(layout, list) and layout:
                preview[f'{key}_layout'] = layout

        # Defaults
        defaults = prefs.get('defaults', {}) if isinstance(prefs, dict) else {}
        if isinstance(defaults, dict) and defaults:
            preview['defaults'] = defaults

        # Feedback
        preview['feedback'] = _get_feedback(s)

        return Response(preview)


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
