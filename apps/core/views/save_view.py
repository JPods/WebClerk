# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/views/save_view.py
from django.http import JsonResponse
# This module provides a Django view for saving (creating or updating) records in a database table via a POST request with JSON payload.
# Classes:
#     WcapiView(View): Handles POST requests to save or update records for a specified table/model.
# Functions:
#     check_field_size(field_value, max_size, field_name):
#         Checks if the serialized size of a field value exceeds the specified maximum size in bytes.
#         Raises ValueError if the size is exceeded.
#     find_model_for_table(table_name: str):
#         Searches all installed Django apps to find and return the model class corresponding to the given table name.
#         Returns None if no matching model is found.
# Constants:
#     ALLOWED_NESTED_KEYS: Dict specifying which nested keys are allowed for certain fields (e.g., 'refs', 'prefs', 'metadata').
#     MAX_FIELD_SIZE: Maximum allowed size (in bytes) for any field value.
# View Details:
#     WcapiView.post(request):
#         - Expects a JSON body with at least 'table_name' and optionally 'id' (for updates).
#         - Finds the corresponding model for the given table name.
#         - Handles both record creation and update.
#         - Validates field sizes and allowed nested keys.
#         - Calls pre-save and post-save asynchronous tasks.
#         - Returns a JSON response indicating success or failure, including error messages for field size violations or integrity errors.
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.services.wcapi_registry import get_model  # explicit registry lookup (replaces dynamic app scan)
from django.apps import apps  # QQQ legacy import retained temporarily (confirm safe to remove)
from django.utils.text import capfirst  # QQQ legacy import retained until full deprecation
import json
from apps.core import tasks
from django.db import IntegrityError
from django.forms.models import model_to_dict
import logging
from django.conf import settings

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

def check_field_size(field_value, max_size, field_name):
    size = len(json.dumps(field_value).encode('utf-8'))
    if size > max_size:
        raise ValueError(f"{field_name} exceeds maximum size of {max_size} bytes")

# Deprecated: dynamic model discovery replaced by explicit allow-list registry (see wcapi_registry.py)
# def find_model_for_table(table_name: str):
#     QQQ confirm no remaining callers, then fully remove
#     ...

class SaveWcapiView(LoginRequiredMixin, View):
    # apply exempt to CSRF for save view actions
    # already passed CSRF protection
    # QQQ frontends must pass CSRF token, so exemption is not needed
    #@csrf_exempt
    #def dispatch(self, *args, **kwargs):
        #return super().dispatch(*args, **kwargs)
    
    def post(self, request):
        # Auth: allow session or JWT; env flag WCAPI_JWT_ONLY can enforce JWT-only.
        from django.conf import settings
        require_jwt = getattr(settings, 'WCAPI_JWT_ONLY', False)
        is_jwt = request.META.get('HTTP_AUTHORIZATION', '').startswith('Bearer ')
        if not request.user.is_authenticated:
            return JsonResponse({'status':'error','message':'Authentication required'}, status=401)
        if require_jwt and not is_jwt:
            return JsonResponse({'status':'error','message':'JWT Bearer token required'}, status=401)
        try:
            # extract JSON data from the request body
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({'status': 'error', 'message': f'Invalid JSON: {e}'}, status=400)

        # get table name and record ID from data
        # QQQ we should add table_name to every json requested by front end
        table_name = data.get('table_name')
        record_id = data.get('id')
        # Version precedence: If-Match header > body.version > body.expected_version (deprecated)
        header_if_match = request.META.get('HTTP_IF_MATCH')  # stub: treat numeric value as expected version
        body_version = data.get('version')
        legacy_expected = data.get('expected_version')
        deprecation_flag = False
        expected_version = None
        if header_if_match:
            header_raw = header_if_match.strip()
            # Accept plain integer or * wildcard (skip check). Future: strong/weak ETag parsing.
            if header_raw == '*':
                expected_version = None  # wildcard skip
            else:
                if header_raw.isdigit():
                    expected_version = int(header_raw)
                else:
                    return JsonResponse({'status': 'error', 'message': f'Malformed If-Match header: {header_raw}'}, status=400)
        elif body_version is not None:
            expected_version = body_version
        elif legacy_expected is not None:
            expected_version = legacy_expected
            deprecation_flag = True

        if not table_name:
            return JsonResponse({'status': 'error', 'message': 'Missing required field: table_name'}, status=400)

        # Registry-based resolution (whitelist enforced). QQQ confirm table_name already validated earlier layers
        model = get_model(table_name)
        if not model:
            return JsonResponse({'status': 'error', 'message': f'Unknown table: {table_name}'}, status=400)

        # Check for special cases
        #if table_name in SPECIAL_CASES:
            #return SPECIAL_CASES[table_name](request, data)

        nested_fields = ['refs', 'prefs', 'metadata']
 
        # is it a new record or an update
        is_update = bool(record_id)

        if is_update:
            try:
                # get the current record
                obj = model.objects.get(id=record_id)
            except model.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Record not found'}, status=404)
            # optimistic concurrency
            if expected_version is not None:
                current_version = getattr(obj, 'version', None)
                if current_version != expected_version:
                    return JsonResponse({'status':'error','message':f'Version conflict: expected {expected_version} got {current_version}'}, status=412)  # 412 Precondition Failed
        else:
            # create an empty record
            obj = model()  # ID will be auto-generated by the database

        # Invoke pre-save task (use apply to avoid broker dependency in tests)
        try:
            tasks.save_pre.apply(args=[table_name, data])  # synchronous if broker unavailable
        except Exception:
            try:
                tasks.save_pre(table_name, data)
            except Exception:
                pass

        
    # Before saving:
        if hasattr(obj, 'pre_save_hook'):
            result = obj.pre_save_hook(data)  # type: ignore[attr-defined]
            if result is not None:
                return JsonResponse({'status': 'error', 'message': result}, status=400)
        # QQQ can this be accomplished with python threading

        field_size_errors = []
        raw_password = None
        for field, value in data.items():
            # Special handling: never assign raw password directly; defer to set_password
            if field == 'password':
                raw_password = value
                continue
            if field in nested_fields and hasattr(obj, field):
                allowed_keys = ALLOWED_NESTED_KEYS.get(field, set())
                current = getattr(obj, field) or {}
                if isinstance(current, str):
                    try:
                        current = json.loads(current)
                    except json.JSONDecodeError:
                        current = {}
                if isinstance(value, dict):
                    for k, v in value.items():
                        if k in allowed_keys:
                            try:
                                check_field_size(v, MAX_FIELD_SIZE, f"{field}.{k}")
                                current[k] = v
                            except ValueError as e:
                                field_size_errors.append(str(e))
                try:
                    check_field_size(current, MAX_FIELD_SIZE, field)
                    setattr(obj, field, current)
                except ValueError as e:
                    field_size_errors.append(str(e))
                    # Do not set the field if the whole dict is too large
            elif field not in ('table_name', 'id') and hasattr(obj, field):
                try:
                    check_field_size(value, MAX_FIELD_SIZE, field)
                    setattr(obj, field, value)
                except ValueError as e:
                    field_size_errors.append(str(e))
        # Apply password hashing if required
        if raw_password is not None and hasattr(obj, 'set_password'):
            try:
                obj.set_password(raw_password)  # type: ignore[attr-defined]
            except Exception as e:  # pragma: no cover - defensive
                return JsonResponse({'status': 'error', 'message': f'Failed to hash password: {e}'}, status=400)

        # Generic model payload validation hook across all tables.
        # Flags:
        #   UNIVERSAL_API_VALIDATE -> apply to any model exposing api_validate_payload(data,is_update)
        #   ORGS_VALIDATE_API -> legacy, orgs-only (preserved for backward compat)
        try:
            universal_flag = getattr(settings, 'UNIVERSAL_API_VALIDATE', False)
        except Exception:
            universal_flag = False
        apply_validation = universal_flag or (table_name == 'orgs' and getattr(settings, 'ORGS_VALIDATE_API', False))
        if apply_validation and hasattr(obj, 'api_validate_payload'):
            try:
                ok, errors = obj.api_validate_payload(data, is_update)  # type: ignore[attr-defined]
            except Exception as e:  # safety net: treat unexpected exceptions as validation failure
                logging.getLogger(__name__).warning(
                    "validation_exception table=%s model=%s error=%s", table_name, model.__name__, e
                )
                return JsonResponse({'status':'error','message':'Validation failed','errors':[str(e)]}, status=400)
            if not ok:
                logging.getLogger(__name__).info(
                    "validation_failed table=%s model=%s errors=%s", table_name, model.__name__, errors
                )
                return JsonResponse({'status': 'error', 'message': 'Validation failed', 'errors': errors}, status=400)

        try:
            obj.save()
        except IntegrityError as e:
            return JsonResponse({'status': 'error', 'message': f'Integrity error: {e}'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Failed to save: {e}'}, status=500)

        # Optional synchronous post-save hook
        post_hook_note = None
        if hasattr(obj, 'post_save_hook'):
            try:
                post_hook_note = obj.post_save_hook(data)  # type: ignore[attr-defined]
            except Exception as e:  # pragma: no cover - defensive
                post_hook_note = f'post_save_hook error: {e}'

        # Invoke post-save task synchronously (avoid broker requirement in tests)
        try:
            tasks.save_post.apply(args=[table_name, data])
        except Exception:
            try:
                tasks.save_post(table_name, data)
            except Exception:
                pass
        # Queue lightweight async fan-out (best effort, ignore failures silently in test/local)
        try:
            if hasattr(tasks, 'save_post_async'):
                tasks.save_post_async.delay(table_name, obj.id, getattr(obj, 'version', None))  # type: ignore[attr-defined]
        except Exception:
            pass
        logger = logging.getLogger(__name__)
        logger.info(f"Saved {table_name} record {obj.id}")  # type: ignore[attr-defined]

        response = {
            'status': 'success',
            'id': obj.id,  # type: ignore[attr-defined]
            'record': model_to_dict(obj),
            'table_name': table_name,
            'version': getattr(obj, 'version', None)
        }
        messages = []
        if field_size_errors:
            messages.extend(field_size_errors)
        if post_hook_note:
            messages.append(post_hook_note)
        if deprecation_flag:
            messages.append("'expected_version' is deprecated; use 'version' or If-Match header")
            logging.getLogger(__name__).warning("Deprecated expected_version field used in save payload for %s", table_name)
        if messages:
            response['messages'] = messages
        return JsonResponse(response)