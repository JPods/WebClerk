# path: apps/core/views/save_view.py
from common.api_responses import api_response
from django.conf import settings
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
from django.db import models
from rest_framework.views import APIView  # type: ignore
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from common.decorators import allow_write
from apps.core.services.wcapi_registry import get_model, normalize_table_key, to_model_name  # explicit registry lookup (replaces dynamic app scan)
import json
from apps.core import tasks
from django.db import IntegrityError
from django.forms.models import model_to_dict
import logging
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiExample
import time
import traceback
from pathlib import Path
from typing import Type, cast

ALLOWED_NESTED_KEYS = {
    'refs': {'tags'},
    'prefs': {'theme', 'lang'},
    'metadata': {'notes'},
}

#SPECIAL_CASES = {
#    'some_special_table': custom_save_function,
    # ...
#}
# YYY 2026-02-15
MAX_FIELD_SIZE = 15000  # bytes, example
UNKNOWN_FIELD_MAX_CHARS = 256  # max len for unknown field values captured into prefs.userdefined

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


def get_nested_value(obj, path: str):
    """Get a nested value from object using dot notation."""
    parts = path.split('.')
    current = obj
    for part in parts:
        if hasattr(current, part):
            current = getattr(current, part)
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def set_nested_value(obj, path: str, value):
    """Set a nested value on object using dot notation."""
    parts = path.split('.')
    current = obj
    for part in parts[:-1]:
        if hasattr(current, part):
            next_obj = getattr(current, part)
            if not isinstance(next_obj, (dict, list)):
                setattr(current, part, {})
                next_obj = getattr(current, part)
            current = next_obj
        elif isinstance(current, dict):
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        else:
            return False
    last = parts[-1]
    if hasattr(current, last):
        setattr(current, last, value)
    elif isinstance(current, dict):
        current[last] = value
    else:
        return False
    return True


def delete_nested_value(obj, path: str):
    """Delete a nested value on object using dot notation."""
    parts = path.split('.')
    current = obj
    for part in parts[:-1]:
        if hasattr(current, part):
            current = getattr(current, part)
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return False
    last = parts[-1]
    if hasattr(current, last):
        setattr(current, last, None)
    elif isinstance(current, dict) and last in current:
        del current[last]
    else:
        return False
    return True

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
    
    #This is documentation and not executed code
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
                description="Update existing contact id=1 using new mode/value structure",
                value={
                    "model_name": "contact",
                    "id": 1,
                    "name_first": {"mode": "update", "value": "fred"},
                    "user1": {"mode": "update", "value": "test of undefined"}
                },
                request_only=True,
            ),
            OpenApiExample(
                name="InsertContact",
                description="Create new contact without id",
                value={
                    "model_name": "contact",
                    "name_first": {"mode": "insert", "value": "john"},
                    "email": {"mode": "insert", "value": "john@example.com"}
                },
                request_only=True,
            ),
            OpenApiExample(
                name="DeleteField",
                description="Delete a field from existing record",
                value={
                    "model_name": "contact",
                    "id": 1,
                    "obsolete_field": {"mode": "delete"}
                },
                request_only=True,
            ),
            OpenApiExample(
                name="NestedUpdate",
                description="Update nested properties using dot notation",
                value={
                    "model_name": "action", 
                    "id": 107,
                    "comments.notes": {"mode": "update", "value": "new notes"}
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
        description="Create or update a record by model_name using universal field operations. Each field must specify a mode ('update', 'insert', 'delete') with optional value. If id is provided, updates that record; otherwise creates a new record. Returns JSON envelope with saved record and messages."
    )

    def post(self, request):
        # Auth: allow session or JWT; env flag WCAPI_JWT_ONLY can enforce JWT-only.
        require_jwt = getattr(settings, 'WCAPI_JWT_ONLY', False)
        is_jwt = request.META.get('HTTP_AUTHORIZATION', '').startswith('Bearer ')
        if not request.user.is_authenticated:
            return api_response(success=False, status_code=401, message='Authentication required', error={'code':'not_authenticated','details':'Authentication required'})
        if require_jwt and not is_jwt:
            # QQQ Check for expired token?
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
        norm_key = normalize_table_key(raw_model_name) # to make is singular form
        if not norm_key:
            return api_response(success=False, status_code=400, message=f'Unknown model: {raw_model_name}', error={'code':'unknown_model','details':f'Unknown model: {raw_model_name}'})
        # this will get the real data object from our models folder
        model = get_model(norm_key)
        if not model:
            return api_response(success=False, status_code=400, message=f'Unknown model: {raw_model_name}', error={'code':'unknown_model','details':f'Unknown model: {raw_model_name}'})
        model_cls = cast(Type[models.Model], model)
        model_key = to_model_name(model_cls) or raw_model_name

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

        # Create or update
        is_update = bool(record_id)
        if is_update:
            try:
                obj = model_cls.objects.get(id=record_id)
            except model_cls.DoesNotExist:  # type: ignore[attr-defined]
                return api_response(success=False, status_code=404, message='Record not found', error={'code':'not_found','details':'Record not found'})
            if expected_version is not None:
                current_version = getattr(obj, 'version', None)
                if current_version != expected_version:
                    return api_response(success=False, status_code=412, message='Version conflict', error={'code':'version_conflict','details': {'expected': expected_version, 'current': current_version}})
        else:
            obj = model_cls()

        try:
            #QQQ explain why we have this
            # list all flatten fields of the model
            json_field_names = {
                f.name for f in obj._meta.get_fields()
                if hasattr(f, 'attname') and isinstance(f, models.JSONField)
            }
        except Exception:
            json_field_names = set()

        # Pre-save hook or task (run synchronously for validation)
        pre_hook = getattr(obj, 'pre_save_hook', None)
        if callable(pre_hook):
            context = {
                'model_name': model_key,
                'is_update': is_update,
                'user_id': getattr(request.user, 'id', None),
            }
            ### QQQ why three time nested?
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
            # Execute save hooks from Setting records
            try:
                from apps.core.constants.save_hooks import execute_save_hook
                hook_result = execute_save_hook(model_key, 'save_pre', obj, data)
                if not hook_result['success']:
                    return api_response(success=False, status_code=400, message='Pre-save hook failed', error={'code':'hook_failed','details': hook_result['errors']})
            except ImportError:
                pass  # Graceful degradation if save_hooks module not available

            try:
                tasks.save_pre.run(model_key, data)
            except Exception:
                try:
                    tasks.save_pre(model_key, data)
                except Exception:
                    pass

        # Assign fields
        field_size_errors = []
        raw_password = None
        for field, field_data in data.items():
            # ignore these fields
            if field == 'password':
                if isinstance(field_data, dict) and 'value' in field_data:
                    raw_password = field_data['value']
                else:
                    raw_password = field_data
                continue
            if field in ('model_name', 'id', 'version', 'expected_version'):
                continue

            # Require new structure: field_data must be {"mode|task": "update|insert|delete", "value": ...} or {"mode|task": "delete"}
            if not isinstance(field_data, dict) or ('mode' not in field_data and 'task' not in field_data):
                return api_response(success=False, status_code=400, message=f'Invalid field format for {field}', error={'code':'invalid_field_format','details':f'Field {field} must be an object with "mode" or "task" key'})

            # Extract mode from 'mode' or 'task' key
            if 'mode' in field_data:
                mode = field_data['mode']
            elif 'task' in field_data:
                mode = field_data['task']
            else:
                mode = 'update'
            value = field_data.get('value')

            if mode not in ('update', 'insert', 'delete'):
                continue  # Invalid mode, skip

            if mode == 'delete':
                # Delete the field
                if '.' in field:
                    delete_nested_value(obj, field)
                else:
                    if hasattr(obj, field):
                        setattr(obj, field, None)
                continue

            # For update/insert, set the value
            if value is None:
                continue

            # Check size
            try:
                check_field_size(value, MAX_FIELD_SIZE, field)
            except ValueError as e:
                field_size_errors.append(str(e))
                continue

            if '.' in field:
                # Nested field
                set_nested_value(obj, field, value)
            else:
                # Regular field
                if hasattr(obj, field):
                    current = getattr(obj, field)
                    is_json_field = field in json_field_names or isinstance(current, dict)
                    if isinstance(value, dict) and is_json_field:
                        if isinstance(current, str):
                            try:
                                current = json.loads(current)
                            except json.JSONDecodeError:
                                current = {}
                        if not isinstance(current, dict):
                            current = {}
                        merged = deep_merge_dict(current, value)
                        setattr(obj, field, merged)
                    else:
                        setattr(obj, field, value)
                else:
                    # Unknown field, move to prefs.userdefined
                    try:
                        prefs = getattr(obj, 'prefs', {}) or {}
                        if isinstance(prefs, str):
                            try:
                                prefs = json.loads(prefs)
                            except json.JSONDecodeError:
                                prefs = {}
                        userdefined = prefs.setdefault('userdefined', {})
                        storable = value
                        try:
                            raw_json = json.dumps(storable)
                            if len(raw_json.encode('utf-8')) > MAX_FIELD_SIZE:
                                storable = str(storable)[:UNKNOWN_FIELD_MAX_CHARS]
                        except Exception:
                            storable = str(storable)[:UNKNOWN_FIELD_MAX_CHARS]
                        userdefined[field] = storable
                        check_field_size(prefs, MAX_FIELD_SIZE, 'prefs')
                        setattr(obj, 'prefs', prefs)
                    except ValueError as e:
                        field_size_errors.append(str(e))

        if raw_password is not None and hasattr(obj, 'set_password'):
            try:
                obj.set_password(raw_password)  # type: ignore[attr-defined]
            except Exception as e:
                return api_response(success=False, status_code=400, message='Failed to hash password', error={'code':'hash_password','details':str(e)})

        ### QQQ what is this?
        # Optional model-level payload validation
        try:
            universal_flag = getattr(settings, 'UNIVERSAL_API_VALIDATE', False)
        except Exception:
            universal_flag = False
        apply_validation = universal_flag or (norm_key == 'orgs' and getattr(settings, 'ORGS_VALIDATE_API', False))
        if apply_validation and hasattr(obj, 'api_validate_payload'):
            try:
                ok, errors = obj.api_validate_payload(data, is_update)  # type: ignore[attr-defined]
            except Exception as e:
                logging.getLogger(__name__).warning(
                    "validation_exception model=%s class=%s error=%s", model_key, model_cls.__name__, e
                )
                return api_response(success=False, status_code=400, message='Validation failed', error={'code':'validation_exception','details': [str(e)]})
            if not ok:
                logging.getLogger(__name__).info(
                    "validation_failed model=%s class=%s errors=%s", model_key, model_cls.__name__, errors
                )
                return api_response(success=False, status_code=400, message='Validation failed', error={'code':'validation_failed','details': errors})

        # Save
        try:
            obj.save()
        except IntegrityError as e:
            return api_response(success=False, status_code=400, message='Integrity error', error={'code':'integrity_error','details': str(e)})
        except Exception as e:
            return api_response(success=False, status_code=500, message='Failed to save', error={'code':'save_failed','details': str(e)})

        obj_id = getattr(obj, 'id', None)

        # Post-save hook or task
        post_hook_note = None
        post_hook = getattr(obj, 'post_save_hook', None)
        if callable(post_hook):
            try:
                context = {
                    'model_name': model_key,
                    'is_update': is_update,
                    'user_id': getattr(request.user, 'id', None),
                }
                try:
                    post_hook_note = post_hook(data, is_update, context)  # type: ignore[misc]
                except TypeError:
                    try:
                        post_hook_note = post_hook(data, is_update)  # type: ignore[misc]
                    except TypeError:
                        post_hook_note = post_hook(data)  # type: ignore[misc]
            except Exception as e:
                post_hook_note = f'post_save_hook error: {e}'
        else:
            # Execute save hooks from Setting records
            try:
                from apps.core.constants.save_hooks import execute_save_hook
                hook_result = execute_save_hook(model_key, 'save_post', obj, data)
                if not hook_result['success']:
                    post_hook_note = f'Post-save hook failed: {hook_result["errors"]}'
            except ImportError:
                pass  # Graceful degradation if save_hooks module not available

            # Execute save_async hooks asynchronously
            try:
                from apps.core.constants.save_hooks import get_save_hooks
                async_hooks = get_save_hooks(model_key)
                async_hook_found = False
                for hook_name, hook_data in async_hooks.items():
                    if 'save_async' in hook_data and hook_data['save_async']:
                        async_hook_found = True
                        break

                if async_hook_found:
                    try:
                        from apps.core.tasks.cache_tasks import execute_save_async_hooks
                        execute_save_async_hooks.delay(model_key, obj_id, data)
                    except ImportError:
                        pass  # Graceful degradation if tasks module not available
            except ImportError:
                pass  # Graceful degradation if save_hooks module not available

            try:
                tasks.save_post.run(model_key, data)
            except Exception:
                try:
                    tasks.save_post(model_key, data)
                except Exception:
                    pass
        ### QQQ we review this next week, 2026-02-15
        try:
            task_async = getattr(tasks, 'save_post_async', None)
            if task_async is not None:
                start = time.time()
                exc = None
                try:
                    task_async.delay(model_key, obj_id, getattr(obj, 'version', None))
                except Exception as e:
                    exc = e
                end = time.time()
                duration = end - start
                THRESHOLD = getattr(settings, 'SAVE_POST_ASYNC_DELAY_LOG_THRESHOLD', 0.1)
                if exc is not None or duration >= THRESHOLD:
                    try:
                        log_dir = Path(settings.BASE_DIR) / '.local' / 'logs'
                        log_dir.mkdir(parents=True, exist_ok=True)
                        out_path = log_dir / 'delay_notifications.jsonl'
                        likely_cause = 'broker_connection_latency' if exc is None else 'broker_exception'
                        record = {
                            'ts': time.time(),
                            'api': '/wcapi/save/',
                            'model': model_key,
                            'id': getattr(obj, 'id', None),
                            'duration': duration,
                            'exception': repr(exc) if exc else None,
                            'trace': traceback.format_exc() if exc else None,
                            'likely_cause': likely_cause,
                        }
                        with open(out_path, 'a', encoding='utf-8') as fh:
                            fh.write(json.dumps(record) + '\n')
                    except Exception:
                        logging.getLogger(__name__).exception('Failed to write delay notification record')
                    logging.getLogger(__name__).warning('save_post_async delayed/errored table=%s id=%s duration=%.3fs exc=%s', model_key, obj_id, duration, exc)
        except Exception:
            logging.getLogger(__name__).exception('Unexpected error measuring save_post_async')

        # Run keyword generation in a thread (not blocking API response)
        try:
            if hasattr(obj, 'update_keywords'):
                import threading
                def update_keywords_async():
                    try:
                        logging.getLogger(__name__).info('Starting keyword update for %s id=%s', model_key, obj_id)
                        obj.update_keywords()
                        logging.getLogger(__name__).info('Calling save for keywords update for %s id=%s', model_key, obj_id)
                        obj.save(update_fields=['refs', 'metadata'])
                        logging.getLogger(__name__).info('Keyword update completed successfully for %s id=%s', model_key, obj_id)
                    except Exception:
                        logging.getLogger(__name__).exception('Failed to update keywords for %s id=%s', model_key, obj_id)
                thread = threading.Thread(target=update_keywords_async)
                thread.daemon = True
                thread.start()
        except Exception:
            logging.getLogger(__name__).exception('Failed to start keyword update thread for %s id=%s', model_key, obj_id)

        # this is needed to pass out to id of a new record
        try:
            safe_fields = [f.name for f in obj._meta.concrete_fields]
            record = model_to_dict(obj, fields=safe_fields)
        except Exception:
            record = {'id': getattr(obj, 'id', None)}
        payload = {
            'id': obj_id,
            'record': record,
            'model_name': model_key,
            'version': getattr(obj, 'version', None)
        }
        messages = []
        if field_size_errors:
            messages.extend(field_size_errors)
        if post_hook_note:
            messages.append(post_hook_note)
        if deprecation_flag:
            messages.append("'expected_version' is deprecated; use 'version' or If-Match header")
            logging.getLogger(__name__).warning("Deprecated expected_version field used in save payload for %s", model_key)
        if messages:
            payload['messages'] = messages
        return api_response(data=payload)