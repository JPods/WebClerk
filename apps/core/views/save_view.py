# path: apps/core/views/save_view.py
from django.http import JsonResponse
from common.api_responses import api_response
# This module provides a Django view for saving (creating or updating) records in a database table via a POST request with JSON payload.
# Classes:
#     WcapiView(View): Handles POST requests to save or update records for a specified table/model.
# Functions:
#     check_field_size(field_value, max_size, field_name):
#         Checks if the serialized size of a field value exceeds the specified maximum size in bytes.
#         Raises ValueError if the size is exceeded.
#     find_model_for_table(model_name: str):
#         Searches all installed Django apps to find and return the model class corresponding to the given table name.
#         Returns None if no matching model is found.
# Constants:
#     ALLOWED_NESTED_KEYS: Dict specifying which nested keys are allowed for certain fields (e.g., 'refs', 'prefs', 'metadata').
#     MAX_FIELD_SIZE: Maximum allowed size (in bytes) for any field value.
# View Details:
#     WcapiView.post(request):
#         - Expects a JSON body with 'model_name' (singular) and optionally 'id' (for updates).
#         - Finds the corresponding model for the given table name.
#         - Handles both record creation and update.
#         - Validates field sizes and allowed nested keys.
#         - Calls pre-save and post-save asynchronous tasks.
#         - Returns a JSON response indicating success or failure, including error messages for field size violations or integrity errors.
from django.views import View
from django.db import models
from rest_framework.views import APIView  # type: ignore
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from common.decorators import allow_write
from apps.core.services.wcapi_registry import get_model, normalize_table_key, to_model_name  # explicit registry lookup (replaces dynamic app scan)
import json
from apps.core import tasks
from apps.core.tasks import perform_save_operation, update_keywords_task
from django.db import IntegrityError
from django.forms.models import model_to_dict
import logging
from django.conf import settings
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiExample
import time
import traceback
from pathlib import Path

ALLOWED_NESTED_KEYS = {
    'refs': {'tags'},
    'prefs': {'theme', 'lang'},
    'metadata': {'notes'},
}

#SPECIAL_CASES = {
#    'some_special_table': custom_save_function,
    # ...
#}

MAX_FIELD_SIZE = 15000  # bytes, example
UNKNOWN_FIELD_MAX_CHARS = 120  # max len for unknown field values captured into prefs.userdefined

def check_field_size(field_value, max_size, field_name):
    size = len(json.dumps(field_value).encode('utf-8'))
    if size > max_size:
        raise ValueError(f"{field_name} exceeds maximum size of {max_size} bytes")


def deep_merge_dict(a: dict, b: dict) -> dict:
    """Recursively merge dict b into dict a (in place) and return a.
    - protects dictionary structures
    - If a[key] and b[key] are both dicts, merge recursively.
    - Otherwise, b[key] overwrites a[key].
    """
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            deep_merge_dict(a[k], v)
        else:
            a[k] = v
    return a

# Deprecated: dynamic model discovery replaced by explicit allow-list registry (see wcapi_registry.py)
# def find_model_for_table(model_name: str):
#     QQQ confirm no remaining callers, then fully remove
#     ...

@method_decorator(csrf_exempt, name='dispatch')
@allow_write
class SaveWcapiView(APIView):
    # apply exempt to CSRF for save view actions
    # already passed CSRF protection
    #def dispatch(self, *args, **kwargs):
        #return super().dispatch(*args, **kwargs)
    
    @extend_schema(
        operation_id="wcapi_save_create_update",
        request=inline_serializer(
            name="WcapiSaveRequest",
            fields={
                'model_name': serializers.CharField(),
                'id': serializers.IntegerField(required=False),
                'version': serializers.IntegerField(required=False),
                'expected_version': serializers.IntegerField(required=False),
                # arbitrary model fields accepted; unknown fields may be captured into prefs.userdefined
            }
        ),
        responses={
            200: inline_serializer(
                name="WcapiSaveEnvelope",
                fields={
                    'status': serializers.CharField(),
                    'error': serializers.JSONField(required=False, allow_null=True),
                    'code': serializers.IntegerField(),
                    'message': serializers.CharField(allow_blank=True),
                    'data': inline_serializer(
                        name="WcapiSaveResponse",
                        fields={
                            'id': serializers.IntegerField(),
                            'model_name': serializers.CharField(),
                            'version': serializers.IntegerField(required=False, allow_null=True),
                            'record': serializers.DictField(),
                            'messages': serializers.ListField(child=serializers.CharField(), required=False),
                        }
                    ),
                }
            ),
            400: inline_serializer(name='WcapiSaveError', fields={'detail': serializers.CharField(required=False)}),
            401: inline_serializer(name='WcapiSaveAuthError', fields={'detail': serializers.CharField(required=False)}),
            412: inline_serializer(name='WcapiSaveVersionConflict', fields={'detail': serializers.CharField(required=False)}),
        },
        examples=[
            OpenApiExample(
                name="UpdateContact",
                description="Update existing contact id=1; unknown fields are ignored or captured in prefs.userdefined",
                value={
                    "model_name": "contact",
                    "id": 1,
                    "name_first": "fred",
                    "user1": "test of undefined",
                    "needtoremove": "find a way"
                },
                request_only=True,
            ),
            OpenApiExample(
                name="SaveResponse",
                description="Response after save (update or create)",
                value={
                    "status": "success",
                    "error": None,
                    "code": 200,
                    "message": "",
                    "data": {
                        "id": 1,
                        "model_name": "contact",
                        "version": 2,
                        "record": {"id": 1, "name_first": "fred", "role": "user"},
                        "messages": []
                    }
                },
                response_only=True,
            ),
        ],
        description="Create or update a record by model_name. If id is provided, updates that record; otherwise creates a new record. Returns JSON envelope with saved record and messages."
    )
    def post(self, request):
        # Auth: allow session or JWT; env flag WCAPI_JWT_ONLY can enforce JWT-only.
        from django.conf import settings
        require_jwt = getattr(settings, 'WCAPI_JWT_ONLY', False)
        is_jwt = request.META.get('HTTP_AUTHORIZATION', '').startswith('Bearer ')
        if not request.user.is_authenticated:
            return api_response(success=False, status_code=401, message='Authentication required', error={'code':'not_authenticated','details':'Authentication required'})
        if require_jwt and not is_jwt:
            return api_response(success=False, status_code=401, message='JWT Bearer token required', error={'code':'jwt_required','details':'JWT Bearer token required'})

        # Parse JSON body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return api_response(success=False, status_code=400, message='Invalid JSON', error={'code':'parse_error','details': str(e)})

        # Required: model_name (singular)
        raw_model_name = data.get('model_name')
        if not raw_model_name:
            return api_response(success=False, status_code=400, message='Missing required field: model_name', error={'code':'missing_model_name','details':'Provide model_name (singular)'})

        # Normalize and resolve model
        norm_key = normalize_table_key(raw_model_name)
        if not norm_key:
            return api_response(success=False, status_code=400, message=f'Unknown model: {raw_model_name}', error={'code':'unknown_model','details':f'Unknown model: {raw_model_name}'})
        model = get_model(norm_key)
        if not model:
            return api_response(success=False, status_code=400, message=f'Unknown model: {raw_model_name}', error={'code':'unknown_model','details':f'Unknown model: {raw_model_name}'})
        model_key = to_model_name(model) or raw_model_name

        # Concurrency: If-Match header > body.version > expected_version (deprecated)
        header_if_match = request.META.get('HTTP_IF_MATCH')
        body_version = data.get('version')
        legacy_expected = data.get('expected_version')
        deprecation_flag = False
        expected_version = None
        if header_if_match:
            header_raw = header_if_match.strip()
            if header_raw == '*':
                expected_version = None
            elif header_raw.isdigit():
                expected_version = int(header_raw)
            else:
                return api_response(success=False, status_code=400, message='Malformed If-Match header', error={'code':'if_match_malformed','details': header_raw})
        elif body_version is not None:
            expected_version = body_version
        elif legacy_expected is not None:
            expected_version = legacy_expected
            deprecation_flag = True

        record_id = data.get('id')

        # Pre-save hook or task (run synchronously for validation)
        is_update = bool(record_id)
        pre_hook = getattr(model(), 'pre_save_hook', None)  # instantiate to check
        if callable(pre_hook):
            context = {
                'model_name': model_key,
                'is_update': is_update,
                'user_id': getattr(request.user, 'id', None),
            }
            try:
                try:
                    result = pre_hook(data, is_update, context)
                except TypeError:
                    try:
                        result = pre_hook(data, is_update)
                    except TypeError:
                        result = pre_hook(data)
            except Exception as e:
                return api_response(success=False, status_code=400, message='Pre-save validation failed', error={'code':'validation_exception','details': str(e)})
            if result is not None:
                if isinstance(result, tuple):
                    ok = bool(result[0])
                    msg = result[1] if len(result) > 1 else 'Validation failed'
                    msg_str = str(msg)
                    if not ok:
                        return api_response(success=False, status_code=400, message=msg_str, error={'code':'validation','details': msg_str})
                else:
                    return api_response(success=False, status_code=400, message=str(result), error={'code':'validation','details': str(result)})
        else:
            # Prefer running the task function locally to avoid broker/setup overhead
            # which can add latency to the synchronous save path (avoid task.apply).
            try:
                # Call the underlying task implementation directly (synchronous local call)
                tasks.save_pre.run(model_key, data)
            except Exception:
                try:
                    # Fallback: call the task callable (may execute synchronously)
                    tasks.save_pre(model_key, data)
                except Exception:
                    # Swallow to avoid failing the save due to background hook issues
                    pass

        # Optional model-level payload validation
        try:
            universal_flag = getattr(settings, 'UNIVERSAL_API_VALIDATE', False)
        except Exception:
            universal_flag = False
        apply_validation = universal_flag or (norm_key == 'orgs' and getattr(settings, 'ORGS_VALIDATE_API', False))
        if apply_validation and hasattr(model, 'api_validate_payload'):
            try:
                ok, errors = model().api_validate_payload(data, is_update)
            except Exception as e:
                logging.getLogger(__name__).warning(
                    "validation_exception model=%s class=%s error=%s", model_key, model.__name__, e
                )
                return api_response(success=False, status_code=400, message='Validation failed', error={'code':'validation_exception','details': [str(e)]})
            if not ok:
                logging.getLogger(__name__).info(
                    "validation_failed model=%s class=%s errors=%s", model_key, model.__name__, errors
                )
                return api_response(success=False, status_code=400, message='Validation failed', error={'code':'validation_failed','details': errors})

        # Call Celery task for save operation asynchronously
        perform_save_operation.delay(model_key, data, record_id=record_id, expected_version=expected_version, user_id=getattr(request.user, 'id', None))

        # Call Celery task for updating keywords asynchronously
        if record_id:
            update_keywords_task.delay(model_key, record_id)

        # Respond instantly with success message
        payload = {
            'id': record_id,
            'model_name': model_key,
            'message': 'Save operation initiated. Processing in background.'
        }
        messages = []
        if deprecation_flag:
            messages.append("'expected_version' is deprecated; use 'version' or If-Match header")
            logging.getLogger(__name__).warning("Deprecated expected_version field used in save payload for %s", model_key)
        if messages:
            payload['messages'] = messages
        return api_response(data=payload)