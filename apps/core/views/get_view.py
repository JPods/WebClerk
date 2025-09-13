# path: apps/core/views/get_view.py
from django.http import JsonResponse  # legacy (remove after full migration)
from rest_framework.views import APIView
from rest_framework import permissions
from django.forms.models import model_to_dict
from apps.core.views.related_view import get_related_data
from apps.core.services.view_edit_access import filter_record_for_role
from common.api_responses import api_response
from apps.core.services.wcapi_registry import normalize_table_key, get_model, to_model_name
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer, OpenApiExample
from rest_framework import serializers

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

    @extend_schema(
        operation_id="wcapi_get_retrieve",
        parameters=[
            OpenApiParameter(name='model_name', required=True, type=str),
            OpenApiParameter(name='id', required=False, type=int),
            OpenApiParameter(name='variants_of', required=False, type=int),
            OpenApiParameter(name='project', required=False, type=str),
        ],
        responses={
            200: inline_serializer(name='WcapiGetEnvelope', fields={
                'status': serializers.CharField(),
                'error': serializers.JSONField(required=False, allow_null=True),
                'code': serializers.IntegerField(),
                'message': serializers.CharField(allow_blank=True),
                'data': inline_serializer(name='WcapiGetResponse', fields={
                    'model_name': serializers.CharField(),
                    'record': serializers.DictField(required=False),
                    'results': serializers.ListField(child=serializers.DictField(), required=False),
                    'total': serializers.IntegerField(required=False),
                    'limit': serializers.IntegerField(required=False),
                    'offset': serializers.IntegerField(required=False),
                    'related': serializers.DictField(required=False),
                    'related_errors': serializers.DictField(required=False),
                }),
            })
        },
        examples=[
            OpenApiExample(
                name="WcapiGetContactList",
                description="Example GET /wcapi/get/?model_name=contact list response",
                value={
                    "status": "success",
                    "error": None,
                    "code": 200,
                    "message": "",
                    "data": {
                        "model_name": "contact",
                        "results": [
                            {
                                "id": 9,
                                "uuid": None,
                                "ida": "",
                                "dt_created": 1757637369130,
                                "dt_modified": 1757637369130,
                                "version": 1,
                                "security_level": 0,
                                "is_deleted": False,
                                "is_archived": False,
                                "metadata": {"flags": {"schema_rev": 1}, "access": {"edit": [], "view": []}, "health": {"rating": 0, "accuracy": 0, "freshness": 0, "consistency": 0, "completeness": 0}, "history": {"synced": {"dt": 0, "contact_id": 0}, "created": {"dt": 1757637369130, "contact_id": 0}, "accessed": {"dt": 1757637369130, "contact_id": 0}, "modified": {"dt": 1757637369130, "contact_id": 0}, "verified": {"dt": 0, "contact_id": 0}}, "publish": "", "version": "1.0", "priority": "", "security": "", "undefined": {}, "versioning": {}},
                                "refs": {"tags": [], "links": {"rep": [], "email": [], "items": [], "order": [], "phone": [], "domain": [], "vendor": [], "contact": [], "project": [], "contacts": [], "customer": [], "document": [], "location": [], "manufacturer": []}, "keywords": [], "categories": [], "related_ids": []},
                                "prefs": {"userdefined": {}},
                                "comments": {"notes": [], "public": "", "partner": "", "process": ""},
                                "health_rating": 0,
                                "password": "",
                                "last_login": None,
                                "is_superuser": False,
                                "email": "",
                                "name_first": "fred",
                                "name_last": "",
                                "name_middle": "",
                                "name_prefix": "",
                                "name_suffix": "",
                                "company": "",
                                "title": "",
                                "department": "",
                                "comment": "",
                                "role": "user",
                                "is_active": True,
                                "is_staff": False,
                                "date_joined": "2025-09-12T00:36:09.130497+00:00",
                                "groups": [],
                                "user_permissions": []
                            }
                        ],
                        "total": 9,
                        "limit": None,
                        "offset": 0
                    }
                },
                request_only=False,
                response_only=True,
            )
            ,
            OpenApiExample(
                name="WcapiGetContactDetail",
                description="Example GET /wcapi/get/?model_name=contact&id=1 detail response including related",
                value={
                    "status": "success",
                    "error": None,
                    "code": 200,
                    "message": "",
                    "data": {
                        "model_name": "contact",
                        "record": {
                            "id": 1,
                            "uuid": None,
                            "ida": "contact_0",
                            "dt_created": 1757535492500,
                            "dt_modified": 1757535492500,
                            "version": 1,
                            "security_level": 0,
                            "is_deleted": False,
                            "is_archived": False,
                            "metadata": {
                                "flags": {"schema_rev": 1},
                                "access": {"edit": [], "view": []},
                                "health": {"rating": 0, "accuracy": 0, "freshness": 0, "consistency": 0, "completeness": 0},
                                "history": {"synced": {"dt": 0, "contact_id": 0}, "created": {"dt": 1757535492500, "contact_id": 0}, "accessed": {"dt": 1757535492500, "contact_id": 0}, "modified": {"dt": 1757535492500, "contact_id": 0}, "verified": {"dt": 0, "contact_id": 0}},
                                "publish": "", "version": "1.0", "priority": "", "security": "", "undefined": {}, "versioning": {}
                            },
                            "refs": {
                                "tags": [],
                                "links": {"emails": [2, 5], "phones": [4], "actions": [4], "domains": [5]},
                                "keywords": [],
                                "categories": [],
                                "related_ids": []
                            },
                            "prefs": {"userdefined": {}},
                            "comments": {"notes": [], "public": "", "partner": "", "process": ""},
                            "health_rating": 0,
                            "password": "contact_0",
                            "last_login": "2025-09-10T20:18:12.500650+00:00",
                            "is_superuser": False,
                            "email": "contact_0",
                            "name_first": "contact_0",
                            "name_last": "contact_0",
                            "name_middle": "contact_0",
                            "name_prefix": "contact_0",
                            "name_suffix": "contact_0",
                            "company": "contact_0",
                            "title": "contact_0",
                            "department": "contact_0",
                            "comment": "",
                            "role": "user",
                            "is_active": True,
                            "is_staff": False,
                            "date_joined": "2025-09-10T20:18:12.500783+00:00",
                            "groups": [],
                            "user_permissions": [20, 268, 40]
                        },
                        "related": {
                            "emails": [
                                {"id": 2, "ida": "email_1", "email": "email_1", "is_primary": False, "is_verified": False},
                                {"id": 5, "ida": "email_4", "email": "email_4", "is_primary": False, "is_verified": False}
                            ],
                            "phones": [
                                {"id": 4, "ida": "phone_3", "number": "phone_3", "opt_out": False}
                            ],
                            "locations": [
                                {"id": 4, "ida": "location_3", "address1": "location_3", "city": "location_3"}
                            ],
                            "domains": [
                                {"id": 5, "ida": "domain_4", "path": "domain_4", "status": "active"}
                            ],
                            "actions": [
                                {"id": 4, "ida": "action_3", "action": "action_3", "status": "action_3"}
                            ]
                        }
                    }
                },
                request_only=False,
                response_only=True,
            )
        ],
        description="List or retrieve records from the registry by model_name. Returns JSON envelope with results and basic pagination fields.",
    )
    def get(self, request):  # noqa: C901 (simple flow)
        from django.conf import settings
        require_jwt = getattr(settings, 'WCAPI_JWT_ONLY', False)
        open_read = getattr(settings, 'WCAPI_OPEN_READ', False)
        is_jwt = bool(getattr(request, 'auth', None)) or request.META.get('HTTP_AUTHORIZATION', '').startswith('Bearer ')
        if not request.user.is_authenticated and not open_read:
            return api_response(
                success=False,
                status_code=401,
                message='Authentication required',
                error={'code': 'not_authenticated', 'details': 'Authentication required'},
            )
        if require_jwt and not is_jwt and not (open_read and not request.user.is_authenticated):
            return api_response(
                success=False,
                status_code=401,
                message='JWT required (missing Bearer token)',
                error={'code': 'jwt_required', 'details': 'JWT required (missing Bearer token)'},
            )

        # Require model_name (singular)
        raw_name = request.GET.get('model_name')
        model_key = normalize_table_key(raw_name) if raw_name else None
        record_id = request.GET.get('id')
        variants_of = request.GET.get('variants_of')
        user_role = getattr(request.user, 'role', 'PUBLIC')

        if not model_key:
            return api_response(
                success=False,
                status_code=400,
                message='Missing model_name',
                error={'code': 'missing_model_name', 'details': 'Provide model_name (singular)'},
            )

        model = get_model(model_key)
        if not model:
            return api_response(
                success=False,
                status_code=400,
                message='Model not found',
                error={'code': 'unknown_model', 'details': f'Model not found for {raw_name}'},
            )

        singular = to_model_name(model_key)

        # Detail record fetch
        if record_id:
            try:
                obj = model.objects.get(id=record_id)
            except model.DoesNotExist:  # type: ignore[attr-defined]
                return api_response(
                    success=False,
                    status_code=404,
                    message='Record not found',
                    error={'code': 'not_found', 'details': 'Record not found'},
                )
            record = model_to_dict(obj)  # type: ignore[arg-type]
            filtered_record = filter_record_for_role(record, singular or '', user_role, 'view')
            related_result = get_related_data(model_key, int(record_id))
            safe_record = {k: self._sanitize(v) for k, v in filtered_record.items()}
            safe_related = (
                {rk: [{sk: self._sanitize(sv) for sk, sv in r.items()} for r in rv] for rk, rv in related_result.get('related', {}).items()}
                if related_result.get('related')
                else {}
            )
            payload = {
                'model_name': singular,
                'record': safe_record,
            }
            if safe_related:
                payload['related'] = safe_related
            if related_result.get('errors'):
                payload['related_errors'] = related_result.get('errors')
            return api_response(data=payload)

        # List
        queryset = model.objects.all()  # type: ignore[attr-defined]

        # Optional variants-of filter for items
        if variants_of and singular == 'item':
            try:
                pid = int(variants_of)
                queryset = queryset.filter(refs__variants__parent_id=pid)  # type: ignore[attr-defined]
            except Exception:
                # Ignore bad input and fall back to unfiltered queryset
                pass

        # Optional small projection for frontend consumption
        proj = request.GET.get('project')
        if proj and singular == 'item':
            allowed = {'id', 'name', 'price', 'quantity'}
            fields = [f for f in (proj.split(',') if isinstance(proj, str) else []) if f in allowed]
            if fields:
                raw_records = [
                    {k: v for k, v in model_to_dict(obj).items() if k in fields}
                    for obj in queryset
                ]
            else:
                raw_records = [
                    filter_record_for_role(model_to_dict(obj), singular or '', user_role, 'view')
                    for obj in queryset
                ]
        else:
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