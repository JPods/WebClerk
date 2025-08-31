# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/views/get_view.py
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import permissions
from django.apps import apps
from django.forms.models import model_to_dict
from apps.core.views.related_view import get_related_data
from apps.core.services.view_edit_access import filter_record_for_role

TABLE_APP_MAP = {
    'contacts': 'core',
    'actions': 'core',
    'emails': 'communications',
    'phones': 'communications',
    'locations': 'communications',
    'domains': 'communications',
    # products
    'items': 'products',  # apps.products.models.item.Item
    # transactions
    'orders': 'transactions',        # Order model
    'orderlines': 'transactions',    # OrderLine model (special-case name below)
    # Add more as needed; prefer adding here to avoid broad app scan cost
}

class OpenReadOrAuthenticated(permissions.BasePermission):
    """Allow unauthenticated read/query when WCAPI_OPEN_READ enabled and JWT not forced."""
    def has_permission(self, request, view):  # pragma: no cover (simple gate)
        from django.conf import settings
        if request.method == 'GET':
            if getattr(settings, 'WCAPI_OPEN_READ', False) and not getattr(settings, 'WCAPI_JWT_ONLY', False):
                return True
        return bool(request.user and request.user.is_authenticated)


class WcapiGetView(APIView):
    """GET access with optional open-read dev mode (set WCAPI_OPEN_READ=1)."""
    permission_classes = [OpenReadOrAuthenticated]

    def _sanitize(self, value):  # pragma: no cover - straightforward
        """Recursively coerce non-JSON-serializable objects to primitives/strings.

        - Allowed primitives: None, bool, int, float, str
        - dict/list traversed
        - datetime/date converted to isoformat
        - other objects -> str(o)
        """
        import datetime, decimal
        from django.db import models as dj_models
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.isoformat()
        if isinstance(value, decimal.Decimal):
            return float(value)
        if isinstance(value, dict):
            return {k: self._sanitize(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._sanitize(v) for v in value]
        if isinstance(value, dj_models.Model):  # collapse model ref to pk or string
            # prefer primary key if available
            pk = getattr(value, 'pk', None)
            return pk if pk is not None else str(value)
        return str(value)

    def get(self, request):  # noqa: C901 (simple flow)
        from django.conf import settings
        require_jwt = getattr(settings, 'WCAPI_JWT_ONLY', False)
        open_read = getattr(settings, 'WCAPI_OPEN_READ', False)
        is_jwt = bool(getattr(request, 'auth', None)) or request.META.get('HTTP_AUTHORIZATION','').startswith('Bearer ')
        if not request.user.is_authenticated and not open_read:
            return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
        if require_jwt and not is_jwt and not (open_read and not request.user.is_authenticated):
            return JsonResponse({'success': False, 'error': 'JWT required (missing Bearer token)'}, status=401)

        table_name = request.GET.get('table_name')
        record_id = request.GET.get('id')
        user_role = getattr(request.user, 'role', 'PUBLIC')
        if not table_name:
            return JsonResponse({'success': False, 'error': 'Missing table_name'}, status=400)
        app_label = TABLE_APP_MAP.get(table_name, 'core')
        # Basic plural -> ModelName heuristic with explicit special cases.
        if table_name == 'addresses':
            model_name = 'Location'  # legacy alias
        elif table_name == 'orderlines':
            model_name = 'OrderLine'
        else:
            model_name = table_name.rstrip('s').capitalize()
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            return JsonResponse({'success': False, 'error': f'Model not found for {table_name}'}, status=400)
        if record_id:
            try:
                obj = model.objects.get(id=record_id)
            except model.DoesNotExist:  # type: ignore[attr-defined]
                return JsonResponse({'success': False, 'error': 'Record not found'}, status=404)
            record = model_to_dict(obj)
            filtered_record = filter_record_for_role(record, table_name, user_role, 'view')
            related_result = get_related_data(table_name, int(record_id))
            safe_record = {k: self._sanitize(v) for k, v in filtered_record.items()}
            safe_related = {rk: [ {sk: self._sanitize(sv) for sk, sv in r.items()} for r in rv ] for rk, rv in related_result.get('related', {}).items()} if related_result.get('related') else {}
            return JsonResponse({'success': True, 'data': safe_record, 'related': safe_related, 'errors': related_result.get('errors', {})})
        # list
        queryset = model.objects.all()  # type: ignore[attr-defined]
        raw_records = [
            filter_record_for_role(model_to_dict(obj), table_name, user_role, 'view')
            for obj in queryset
        ]
        safe_records = [
            {k: self._sanitize(v) for k, v in rec.items()}
            for rec in raw_records
        ]
        return JsonResponse({'success': True, 'data': safe_records})