"""Settings bootstrap API — health check + import/fetch endpoints.

Three endpoints:
    GET  /wcapi/settings-health/     — run health check, return report (staff only)
    POST /wcapi/settings-bootstrap/  — import a settings bundle (staff only)
    POST /wcapi/settings-fetch-hq/   — fetch from webclerk.com (requires Athena token, staff only)
"""
import json
import logging

from django.http import JsonResponse
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)


def _staff_required(view_func):
    """Combined login_required + is_staff check."""
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return JsonResponse({'success': False, 'error': 'Staff access required'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


@method_decorator([login_required, _staff_required], name='dispatch')
class SettingsHealthView(View):
    """GET /wcapi/settings-health/ — returns health check report."""

    def get(self, request):
        from apps.core.services.setting_health import check_settings_health
        report = check_settings_health()
        return JsonResponse(report)


@method_decorator([login_required, _staff_required], name='dispatch')
class SettingsBootstrapView(View):
    """POST /wcapi/settings-bootstrap/ — import a settings bundle.

    Body: JSON settings bundle (list of Setting records with UUIDs).
    Source: git pull → file upload → POST here.
    """

    def post(self, request):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError) as e:
            return JsonResponse(
                {'success': False, 'error': f'Invalid JSON: {e}'},
                status=400,
            )

        from apps.core.services.setting_bootstrap import import_settings_bundle
        result = import_settings_bundle(body)
        result['success'] = not result['errors']

        # Re-run health check after import
        from apps.core.services.setting_health import check_settings_health
        result['health'] = check_settings_health()

        status = 200 if result['success'] else 422
        return JsonResponse(result, status=status)


@method_decorator([login_required, _staff_required], name='dispatch')
class SettingsFetchHqView(View):
    """POST /wcapi/settings-fetch-hq/ — fetch from webclerk.com.

    Body: {"athena_token": "..."}
    webclerk.com IS the path — hardcoded, not configurable.
    No token = 401.
    """

    def post(self, request):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse(
                {'success': False, 'error': 'Invalid JSON'},
                status=400,
            )

        athena_token = body.get('athena_token', '').strip()
        if not athena_token:
            return JsonResponse(
                {'success': False, 'error': 'Athena token required'},
                status=401,
            )

        from apps.core.services.setting_bootstrap import fetch_from_wchq
        result = fetch_from_wchq(athena_token)

        # Re-run health check after fetch
        from apps.core.services.setting_health import check_settings_health
        result['health'] = check_settings_health()

        status = 200 if result.get('success') else 422
        return JsonResponse(result, status=status)
