# path: apps/core/views/get_view.py
from django.http import JsonResponse  # legacy (remove after full migration)
from rest_framework.views import APIView
from rest_framework import permissions
from django.forms.models import model_to_dict
from apps.core.views.related_view import get_related_data
from apps.core.services.view_edit_access import filter_record_for_role
from common.api_responses import api_response
from apps.core.services.wcapi_registry import normalize_table_key, get_model, to_model_name

"""This view now resolves models via the registry; no app map needed."""

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
            return api_response(success=False, status_code=401, message='Authentication required', error={'code':'not_authenticated','details':'Authentication required'})
        if require_jwt and not is_jwt and not (open_read and not request.user.is_authenticated):
            return api_response(success=False, status_code=401, message='JWT required (missing Bearer token)', error={'code':'jwt_required','details':'JWT required (missing Bearer token)'})

        # Require model_name (singular)  #chaned from t_n: removed legacy 'table_name'
        raw_name = request.GET.get('model_name')
        table_name = normalize_table_key(raw_name) if raw_name else None
        record_id = request.GET.get('id')
        user_role = getattr(request.user, 'role', 'PUBLIC')
        if not table_name:
            return api_response(success=False, status_code=400, message='Missing model_name', error={'code':'missing_model_name','details':'Provide model_name (singular)'})  #chaned from t_n
        model = get_model(table_name)
        if not model:
            # Keep generic unknown phrasing
            return api_response(success=False, status_code=400, message='Model not found', error={'code':'unknown_model','details':f'Model not found for {raw_name}'})
        singular = to_model_name(table_name)
        if record_id:
            try:
                obj = model.objects.get(id=record_id)
            except model.DoesNotExist:  # type: ignore[attr-defined]
                return api_response(success=False, status_code=404, message='Record not found', error={'code':'not_found','details':'Record not found'})
            record = model_to_dict(obj)  # type: ignore[arg-type]
            filtered_record = filter_record_for_role(record, singular or '', user_role, 'view')
            related_result = get_related_data(table_name, int(record_id))
            safe_record = {k: self._sanitize(v) for k, v in filtered_record.items()}
            safe_related = {rk: [ {sk: self._sanitize(sv) for sk, sv in r.items()} for r in rv ] for rk, rv in related_result.get('related', {}).items()} if related_result.get('related') else {}
            payload = {
                'model_name': singular,
                'record': safe_record,
            }
            if safe_related:
                payload['related'] = safe_related
            if related_result.get('errors'):
                payload['related_errors'] = related_result.get('errors')
            return api_response(data=payload)
        # list
        queryset = model.objects.all()  # type: ignore[attr-defined]
        raw_records = [
            filter_record_for_role(model_to_dict(obj), singular or '', user_role, 'view')
            for obj in queryset
        ]
        safe_records = [
            {k: self._sanitize(v) for k, v in rec.items()}
            for rec in raw_records
        ]
        payload = {
            'model_name': singular,
            'results': safe_records,
            'total': len(safe_records),
            'limit': None,
            'offset': 0,
        }
        return api_response(data=payload)