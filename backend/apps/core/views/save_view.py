# path: apps/core/views/save_view.py
from common.api_responses import api_response
from common.write_through import is_write_through, forward_and_store
from django.conf import settings
import logging
console_logger = logging.getLogger('console')  # Console logger for debugging
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
from django.db import models, transaction, IntegrityError
from rest_framework.views import APIView  # type: ignore
from common.decorators import allow_write
from apps.core.constants.model_registry import get_model, normalize_table_key, to_model_name  # explicit registry lookup
from apps.core.utils import policy
from apps.core.constants.model_registry import get_model_meta
import json
import re
from django.forms.models import model_to_dict
import logging
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiExample
from typing import Type, cast, List, Dict, Any
from common.refs.links import ensure_bidirectional
from common.models import LINK_DENORMALIZE_FIELDS
from apps.core.models import Contact
from apps.core.services.field_behaviors import _I18N_FIELDS as _i18n_field_set
from django.utils import timezone

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


from common.json_path import get_nested_value, set_nested_value, delete_nested_value


def coerce_int(value):
    """Attempt to coerce stringified integers into int; return original on failure."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            try:
                return int(stripped)
            except (TypeError, ValueError):  # defensive
                return value
    return value

# Deprecated: dynamic model discovery replaced by explicit allow-list registry (see model_registry.py)
# def find_model_for_table(model_name: str):
#     QQQ confirm no remaining callers, then fully remove
#     ...

@allow_write
class SaveWcapiView(APIView):
    # CSRF enforced by DRF's SessionAuthentication for cookie-based requests.
    # JWT Bearer requests skip CSRF automatically (not browser-forwardable).

    # NOTE: _perform_save() was removed 2026-02-21 — it was dead code (never
    # called) that duplicated the line-processing + pending-creation logic
    # already present in post().  All save traffic now flows through post().


    #This is documentation and not executed code
    @extend_schema(
        operation_id="wcapi_save_create_update",
        summary="Insert/Update/Delete any model records",
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
        # Demo mode — block all saves at the application layer
        if getattr(settings, 'READ_ONLY_MODE', False):
            return api_response(
                success=False, status_code=405,
                message='This is a read-only demo. Download WebClerk at webclerk.com to modify data.',
                error={'code': 'demo_read_only', 'details': 'Saves are disabled on the demo instance.'})

        # Enhanced logging for debugging
        console_logger.debug(f"[SAVE_VIEW] Starting save operation for request ID: {getattr(request, 'request_id', 'unknown')}")

        # Auth: allow session or JWT; env flag WCAPI_JWT_ONLY can enforce JWT-only.
        require_jwt = getattr(settings, 'WCAPI_JWT_ONLY', False)
        is_jwt = request.META.get('HTTP_AUTHORIZATION', '').startswith('Bearer ')
        if not request.user.is_authenticated:
            console_logger.error(f"[SAVE_VIEW] Authentication failed for user: {getattr(request.user, 'id', 'unknown')}")
            return api_response(success=False, status_code=401, message='Authentication required', error={'code':'not_authenticated','details':'Authentication required'})
        if require_jwt and not is_jwt:
            console_logger.error(f"[SAVE_VIEW] JWT required but not found")
            # QQQ Check for expired token?
            return api_response(success=False, status_code=401, message='JWT Bearer token required', error={'code':'jwt_required','details':'JWT Bearer token required'})
        
        console_logger.info(f"[SAVE_VIEW] Authentication passed for user: {getattr(request.user, 'id', 'unknown')}")

        # Observer mode — read-only users cannot save
        try:
            profile = getattr(request.user, 'userprofile', None)
            if profile and getattr(profile, 'role', '') == 'observer':
                return api_response(success=False, status_code=403, message='Observer mode — read only',
                                    error={'code': 'observer_readonly', 'details': 'Demo observer accounts cannot modify data.'})
        except Exception:
            pass

        # Parse JSON body - use request.data if available (DRF already parsed), fallback to body
        try:
            console_logger.debug(f"[SAVE_VIEW] Parsing JSON body...")
            if hasattr(request, 'data') and request.data:
                data = dict(request.data)
            else:
                data = json.loads(request.body)
        except json.JSONDecodeError as e:
            console_logger.error(f"[SAVE_VIEW] JSON parse error: {e}")
            return api_response(success=False, status_code=400, message='Invalid JSON', error={'code':'parse_error','details': str(e)})

        # Log all keys for debugging dot-path support
        dot_keys = [k for k in data.keys() if '.' in k or '[' in k]
        if dot_keys:
            console_logger.warning(f"[SAVE_VIEW] DOT-PATH KEYS in payload: {dot_keys}")

        # Convert HTML checkbox values: "on" -> True, "off" -> False
        for key, value in list(data.items()):
            if value == 'on':
                data[key] = True
            elif value == 'off':
                data[key] = False

        # Handle nested 'data' key for compatibility with some clients
        # Models that previously had a 'data' field now use 'config'.
        # If 'data' key contains a dict and the model doesn't have a 'data' column, merge it into the payload.
        if 'data' in data and isinstance(data['data'], dict):
            model_key = data.get('model_name') or data.get('model') or ''
            has_data_field = False
            try:
                from apps.core.utils.registry import resolve
                resolved = resolve(model_key)
                # resolve() may return a ModelMeta or the model class directly
                if resolved is not None:
                    cls = resolved.import_model() if hasattr(resolved, 'import_model') else resolved
                    if hasattr(cls, '_meta'):
                        has_data_field = any(f.name == 'data' for f in cls._meta.get_fields() if hasattr(f, 'column'))
            except Exception as e:
                console_logger.warning(f"[SAVE_VIEW] data-field check failed for {model_key}: {e}")
            if not has_data_field:
                data.update(data['data'])
                del data['data']
                console_logger.info(f"[SAVE_VIEW] Merged 'data' fields into payload")
            else:
                console_logger.info(f"[SAVE_VIEW] Preserved 'data' field for model {model_key}")

        # Handle nested 'record' key (used by R25 saveTransactionWithLines)
        if 'record' in data and isinstance(data['record'], dict):
            record_data = data['record']
            # Preserve model_name, id, and options at top level
            model_name = data.get('model_name')
            record_id = data.get('id')
            options = data.get('options')
            data.update(record_data)
            # Restore top-level fields that may have been overwritten
            if model_name:
                data['model_name'] = model_name
            if record_id:
                data['id'] = record_id
            if options:
                data['options'] = options
            # Remove the record key itself — its contents are now at top level
            del data['record']
            console_logger.info(f"[SAVE_VIEW] Merged 'record' fields into payload, lines count: {len(data.get('lines', []))}")

        # If client provided a project_slug but not a numeric project_id, try to resolve it here.
        try:
            if 'project_slug' in data and 'project_id' not in data:
                slug_val = data.get('project_slug')
                if isinstance(slug_val, str) and slug_val:
                    proj_model = get_model('project') or get_model('projects')
                    if proj_model is not None:
                        try:
                            proj = proj_model.objects.filter(slug=slug_val).first()
                            if proj:
                                data['project_id'] = proj.id
                        except Exception:
                            pass
        except Exception:
            pass

        # Required: model_name (singular)
        raw_model_name = data.get('model_name')
        # If model_name not found in data, check query params
        if not raw_model_name:
            raw_model_name = request.query_params.get('model_name')
            if raw_model_name:
                data['model_name'] = raw_model_name
        if not raw_model_name:
            console_logger.error(f"[SAVE_VIEW] Missing model_name")
            return api_response(success=False, status_code=400, message='Missing required field: model_name', error={'code':'missing_model_name','details':'Provide model_name (singular)'})

        console_logger.debug(f"[SAVE_VIEW] Processing model_name: {raw_model_name}")

        # Normalize and resolve model
        norm_key = normalize_table_key(raw_model_name) # to make is singular form
        if not norm_key:
            console_logger.error(f"[SAVE_VIEW] Unknown model after normalization: {raw_model_name}")
            return api_response(success=False, status_code=400, message=f'Unknown model: {raw_model_name}', error={'code':'unknown_model','details':f'Unknown model: {raw_model_name}'})
        # this will get the real data object from our models folder
        model = get_model(norm_key)
        if not model:
            console_logger.error(f"[SAVE_VIEW] Model not found for key: {norm_key}")
            return api_response(success=False, status_code=400, message=f'Unknown model: {raw_model_name}', error={'code':'unknown_model','details':f'Unknown model: {raw_model_name}'})
        model_cls = cast(Type[models.Model], model)
        model_key = to_model_name(model_cls) or raw_model_name
        console_logger.debug(f"[SAVE_VIEW] Model resolved: {model_key} (class: {model_cls.__name__})")

        # Log setting saves for debugging layout persistence
        if model_key == 'setting' and data.get('purpose') in ('wc:workbench_fields', 'wc:model'):
            _data = data.get('data', {})
            _list_preview = [f.get('field') if isinstance(f, dict) else f for f in (_data.get('list') or [])[:4]] if isinstance(_data, dict) else '?'
            console_logger.warning(f"[SAVE_VIEW] SETTING SAVE id={data.get('id')} parent_model={data.get('parent_model')} list_preview={_list_preview}")

        # Saved searches are global admin-managed settings.
        if model_key == 'setting':
            purpose_value = data.get('purpose')
            tentative_record_id = coerce_int(data.get('id') or request.query_params.get('id'))
            if purpose_value is None and tentative_record_id:
                try:
                    purpose_value = model_cls.objects.filter(id=tentative_record_id).values_list('purpose', flat=True).first()
                except Exception:
                    purpose_value = None

            if str(purpose_value or '').strip().lower() == 'search':
                user = getattr(request, 'user', None)
                is_admin_writer = bool(
                    user
                    and getattr(user, 'is_authenticated', False)
                    and (
                        getattr(user, 'is_superuser', False)
                        or getattr(user, 'is_staff', False)
                        or str(getattr(user, 'role', '')).lower() == 'admin'
                    )
                )
                if not is_admin_writer:
                    return api_response(
                        success=False,
                        status_code=403,
                        message='Only admin users can create or update saved searches',
                        error={'code': 'saved_search_admin_required'},
                    )

        # Concurrency: If-Match header > body.version > expected_version (deprecated)
        header_if_match = request.META.get('HTTP_IF_MATCH')
        body_version = coerce_int(data.get('version'))
        legacy_expected = coerce_int(data.get('expected_version'))
        deprecation_flag = False
        expected_version = None
        if header_if_match:
            header_raw = header_if_match.strip()
            if header_raw == '*':
                expected_version = None
            elif header_raw.isdigit():
                expected_version = int(header_raw)
            else:
                console_logger.error(f"[SAVE_VIEW] Malformed If-Match header: {header_raw}")
                return api_response(success=False, status_code=400, message='Malformed If-Match header', error={'code':'if_match_malformed','details': header_raw})
        elif body_version is not None:
            expected_version = body_version
        elif legacy_expected is not None:
            expected_version = legacy_expected
            deprecation_flag = True

        record_id = data.get('id')
        # If id not found in data, check query params
        if record_id is None:
            record_id = request.query_params.get('id')
            if record_id is not None:
                data['id'] = record_id
        record_id = coerce_int(record_id)
        data['id'] = record_id
        console_logger.debug(f"[SAVE_VIEW] Record ID: {record_id}, Expected version: {expected_version}")

        # ── Write-through: forward to remote, store bundle locally ──
        if is_write_through():
            console_logger.info(f"[SAVE_VIEW] Write-through mode — forwarding {model_key} save to remote DB")
            wt_payload, wt_status = forward_and_store(request, model_cls, data)
            if wt_status >= 400:
                return api_response(
                    success=False, status_code=wt_status,
                    message=wt_payload.get('detail', 'Write-through failed'),
                    error={'code': 'write_through_error', 'details': wt_payload},
                )
            return api_response(data=wt_payload, status_code=wt_status)

        # Create or update — wrapped in transaction.atomic for data integrity.
        # All saves (parent + lines) succeed or fail together.
        try:
            return self._save_record(request, model_cls, model_key, norm_key, data, record_id, expected_version, deprecation_flag)
        except IntegrityError as e:
            console_logger.error(f"[SAVE_VIEW] Integrity error during save: {e}")
            return api_response(success=False, status_code=400, message='Integrity error', error={'code':'integrity_error','details': str(e)})
        except ValueError as e:
            console_logger.error(f"[SAVE_VIEW] Value error during save: {e}")
            return api_response(success=False, status_code=400, message='Invalid field values', error={'code':'invalid_field','details': str(e)})
        except Exception as e:
            console_logger.error(f"[SAVE_VIEW] Exception during save: {e}")
            return api_response(success=False, status_code=500, message='Failed to save', error={'code':'save_failed','details': str(e)})

    @staticmethod
    def _adjust_source_line(source: dict, target_model: str, line_qty: float, line_obj):
        """After creating a new line from conversion, adjust the source line.

        Each model owns one bucket. The source line adjusts its remaining,
        saves, and fires its own pending. Linear: one thing, then the next.

        Only sell-side conversions adjust source lines:
          order    → proposal_line_id  → ProposalLine (on_p)
          invoice  → order_line_id     → OrderLine    (on_so)
          invoice  → proposal_line_id  → ProposalLine (on_p)  [direct proposal→invoice]

        Purchase does NOT adjust the source order — it's a buy-side action.
        The order's on_so stays committed until an invoice consumes it.
        """
        from apps.core.models import Pending

        # Purchase lines don't adjust source — buy-side doesn't consume sell-side
        if target_model == 'purchase':
            return

        # Determine which source line to adjust.
        source_lookups = [
            ('proposal_line_id', 'apps.transactions.models.proposal_line', 'ProposalLine', 'proposal', 'on_p'),
            ('order_line_id',    'apps.transactions.models.order_line',    'OrderLine',    'order',    'on_so'),
        ]
        source_key = source_id = module_path = class_name = parent_attr = bucket_field = None
        for _key, _mod, _cls, _parent, _bucket in source_lookups:
            _id = source.get(_key)
            if _id:
                source_key, source_id, module_path, class_name, parent_attr, bucket_field = _key, _id, _mod, _cls, _parent, _bucket
                break
        if not source_id:
            return

        import importlib
        mod = importlib.import_module(module_path)
        SourceLine = getattr(mod, class_name)

        src_line = SourceLine.objects.get(pk=source_id)
        sq = dict(src_line.quantity or {})
        s_active = float(sq.get('active', 0) or 0)
        sq['remaining'] = max(0.0, s_active - line_qty)
        src_line.quantity = sq
        src_line.status = 'transferred' if sq['remaining'] <= 0 else src_line.status
        src_line.save(update_fields=['quantity', 'status', 'dt_modified', 'version'])

        # Fire source bucket pending
        item_data = src_line.item or {}
        item_id = item_data.get('item_id') or item_data.get('id') if isinstance(item_data, dict) else None
        if item_id:
            parent_obj = getattr(src_line, parent_attr, None)
            doc_ida = getattr(parent_obj, 'ida', '') if parent_obj else ''
            Pending.objects.create(
                model_name='item',
                record_id=str(item_id),
                purpose='inventory_line_add',
                name=f'{bucket_field} release: {item_data.get("ida_item", item_id)}',
                changes={
                    bucket_field: -line_qty,
                    'reason': f'{parent_attr} line transferred to {target_model}',
                    'doc_id': doc_ida,
                    'line_id': src_line.id,
                    'item_id': item_id,
                },
            )

    @transaction.atomic
    def _save_record(self, request, model_cls, model_key, norm_key, data, record_id, expected_version, deprecation_flag):
        is_update = bool(record_id)
        if is_update:
            console_logger.debug(f"[SAVE_VIEW] Loading existing record with ID: {record_id}")
            try:
                # Use select_for_update() to prevent concurrent modifications.
                # When expected_version is set, include it in the filter so the
                # version check is atomic — no race window between fetch and check.
                if expected_version is not None:
                    try:
                        obj = model_cls.objects.select_for_update().get(id=record_id)
                    except model_cls.DoesNotExist:  # type: ignore[attr-defined]
                        console_logger.error(f"[SAVE_VIEW] Record not found: {record_id}")
                        return api_response(success=False, status_code=404, message='Record not found', error={'code':'not_found','details':'Record not found'})
                    current_version = getattr(obj, 'version', None)
                    if current_version is not None and current_version != expected_version:
                        console_logger.warning(f"[SAVE_VIEW] Version conflict - Current: {current_version}, Expected: {expected_version}")
                        return api_response(success=False, status_code=412, message='Record was modified by another user. Reload and try again.', error={'code':'version_conflict','details': {'expected': expected_version, 'current': current_version}})
                else:
                    obj = model_cls.objects.select_for_update().get(id=record_id)
                console_logger.debug(f"[SAVE_VIEW] Record loaded successfully: {obj}")
            except model_cls.DoesNotExist:  # type: ignore[attr-defined]
                console_logger.error(f"[SAVE_VIEW] Record not found: {record_id}")
                return api_response(success=False, status_code=404, message='Record not found', error={'code':'not_found','details':'Record not found'})
        else:
            console_logger.debug(f"[SAVE_VIEW] Creating new record")
            obj = model_cls()

            # Training mode — force qq prefix on all new record idas
            try:
                user_prefs = getattr(request.user, 'prefs', None) or {}
                if isinstance(user_prefs, dict) and user_prefs.get('training'):
                    # Set a marker so post-save ida generation also uses qq prefix
                    obj._training_prefix = 'qq'
            except Exception:
                pass

        try:
            console_logger.debug(f"[SAVE_VIEW] Getting JSON field names...")
            #QQQ explain why we have this
            # list all flatten fields of the model
            json_field_names = {
                f.name for f in obj._meta.get_fields()
                if hasattr(f, 'attname') and isinstance(f, models.JSONField)
            }
            console_logger.debug(f"[SAVE_VIEW] JSON fields found: {json_field_names}")
            # M2M fields cannot be set via setattr — must use .set() after save
            m2m_field_names = {
                f.name for f in obj._meta.get_fields()
                if f.many_to_many or f.one_to_many
            }
        except Exception as e:
            console_logger.warning(f"[SAVE_VIEW] Error getting JSON field names: {e}")
            json_field_names = set()
            m2m_field_names = set()
        
        console_logger.info(f"[SAVE_VIEW] Starting pre-save hooks...")

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

        # ── Role-based write-field filtering ──
        from apps.core.utils.model_policies import enforce_write_policy
        data, denied_fields = enforce_write_policy(model_cls, data, request=request)
        if denied_fields:
            console_logger.info(
                "[SAVE_VIEW] Write-policy stripped fields from %s: %s",
                model_key, ", ".join(denied_fields),
            )

        # ── Field assignment (delegated to save_field_assignment service) ──
        from apps.core.services.save_field_assignment import assign_fields
        _assignment = assign_fields(obj, data, model_cls, json_field_names, m2m_field_names)
        raw_password = _assignment['raw_password']
        field_size_errors = _assignment['field_size_errors']
        field_value_errors = _assignment['field_value_errors']

        if raw_password is not None and hasattr(obj, 'set_password'):
            try:
                obj.set_password(raw_password)  # type: ignore[attr-defined]
            except Exception as e:
                return api_response(success=False, status_code=400, message='Failed to hash password', error={'code':'hash_password','details':str(e)})

        if field_value_errors:
            # Ensure errors are serializable and log request preview for debugging
            err_details = [str(e) for e in field_value_errors]
            console_logger.error(f"[SAVE_VIEW] Field coercion errors for {model_key} ID {record_id}: {err_details}")
            return api_response(success=False, status_code=400, message='Invalid field values', error={'code': 'invalid_field', 'details': err_details})

        # ── Envelope validation (Pydantic schema check on metadata/config/refs/prefs) ──
        from apps.core.services.save_envelope import validate_and_reject
        _envelope_fields = set(data.keys()) & {'metadata', 'config', 'refs', 'prefs'}
        if _envelope_fields:
            envelope_error = validate_and_reject(obj, model_key, _envelope_fields)
            if envelope_error:
                return api_response(
                    success=False, status_code=400,
                    message=f'Envelope validation failed: {envelope_error}',
                    error={'code': 'envelope_invalid', 'details': envelope_error},
                )

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

        console_logger.debug(f"[SAVE_VIEW] Starting database save...")

        # Normalize contact_id: ensure numeric or clear so model can auto-resolve
        try:
            if hasattr(obj, 'contact_id'):
                cid = getattr(obj, 'contact_id')
                if isinstance(cid, str):
                    s = cid.strip()
                    if s.isdigit():
                        setattr(obj, 'contact_id', int(s))
                    else:
                        resolved = None
                        try:
                            assigned = data.get('assigned_to') or data.get('assignedTo')
                            if isinstance(assigned, list) and assigned:
                                first = assigned[0]
                                if isinstance(first, dict):
                                    aid = first.get('id')
                                    name = first.get('name')
                                    if isinstance(aid, str) and aid.isdigit():
                                        resolved = int(aid)
                                    elif isinstance(name, str) and name.strip().isdigit():
                                        resolved = int(name.strip())
                        except Exception:
                            resolved = None
                        if resolved:
                            setattr(obj, 'contact_id', resolved)
                        else:
                            setattr(obj, 'contact_id', 0)
        except Exception:
            pass
        console_logger.debug(f"[SAVE_VIEW] Executing obj.save() for {model_key} ID: {getattr(obj, 'id', 'new')}")
        obj.save()
        console_logger.debug(f"[SAVE_VIEW] Save completed successfully for {model_key} ID: {getattr(obj, 'id', 'new')}")
        # Verify setting save
        if model_key == 'setting' and hasattr(obj, 'purpose') and getattr(obj, 'purpose', '') in ('wc:workbench_fields', 'wc:model'):
            _saved = getattr(obj, 'data', {})
            _list_saved = [f.get('field') if isinstance(f, dict) else f for f in (_saved.get('list') or [])[:4]] if isinstance(_saved, dict) else '?'
            console_logger.warning(f"[SAVE_VIEW] SETTING SAVED id={obj.id} parent_model={getattr(obj, 'parent_model', '?')} list={_list_saved}")

        # ── Denormalize org (customer/vendor/manufacturer) into refs.links ──
        try:
            from apps.transactions.services.denormalize_org_links import denormalize_org_links
            if denormalize_org_links(obj, model_key):
                obj.save(update_fields=['refs', 'version', 'dt_modified'])
                console_logger.debug(f"[SAVE_VIEW] Denormalized org links for {model_key} #{getattr(obj, 'id', '?')}")
        except Exception:
            pass  # non-transaction models will simply return False

        # ── Line processing (delegated to save_line_processing service) ──
        from apps.core.services.save_line_processing import process_lines
        _adjust_fn = getattr(self, '_adjust_source_line', None)
        process_lines(obj, data, model_key, adjust_source_fn=_adjust_fn)

        # ── Auto-link communication records to Contact (delegated to save_contact_linking) ──
        linked = False
        contact = None
        bucket = None
        try:
            comm_models = {"email", "phone", "address", "domain"}
            if model_key.lower() in comm_models:
                bucket = model_key.lower()
                if request.user and getattr(request.user, "is_authenticated", False):
                    contact = Contact.objects.filter(pk=getattr(request.user, "pk", None)).first()
                if contact:
                    from apps.core.services.save_contact_linking import link_comm_to_contact
                    fields = LINK_DENORMALIZE_FIELDS.get(bucket, ["id"]) or ["id"]
                    linked = link_comm_to_contact(obj, contact, bucket, fields)
        except Exception:
            pass

        # Append contact link for action saves
        if model_key == 'action':
            try:
                from apps.core.services.action_links import append_contact_link
                user_id = getattr(request.user, 'id', None)
                if user_id:
                    append_contact_link(obj, user_id)
                    console_logger.debug(f"[SAVE_VIEW] Appended contact link for action ID: {obj.id}")
            except Exception as e:
                console_logger.error(f"[SAVE_VIEW] Failed to append contact link: {e}")
            
            # Auto-schedule action based on parent dependencies (Finish-to-Start)
            # When refs.parents is set, update dt_start to latest parent's dt_end
            try:
                from apps.core.services.action_links import auto_schedule_from_parents
                refs_data = data.get('refs.parents') or data.get('refs', {})
                if isinstance(refs_data, dict) and refs_data.get('value'):
                    refs_data = refs_data.get('value')
                refs_obj = getattr(obj, 'refs', {}) or {}
                if isinstance(refs_obj, dict) and refs_obj.get('parents'):
                    schedule_result = auto_schedule_from_parents(obj, save=True)
                    if schedule_result.get('updated'):
                        console_logger.info(
                            f"[SAVE_VIEW] Auto-scheduled action {obj.id}: dt_start set to {schedule_result.get('dt_start')} "
                            f"(from parent {schedule_result.get('latest_parent_id')})"
                        )
            except Exception as e:
                console_logger.error(f"[SAVE_VIEW] Failed to auto-schedule action: {e}")
            
            # Cascading reschedule: if this action's dates changed, push children forward
            try:
                from apps.core.services.action_links import check_and_reschedule_children
                # Check if dt_start or duration was updated
                dt_start_changed = 'dt_start' in data
                duration_changed = 'duration' in data
                if dt_start_changed or duration_changed:
                    rescheduled = check_and_reschedule_children(obj, save=True)
                    if rescheduled:
                        console_logger.info(
                            f"[SAVE_VIEW] Cascading reschedule: {len(rescheduled)} children rescheduled for action {obj.id}"
                        )
            except Exception as e:
                console_logger.error(f"[SAVE_VIEW] Failed to cascade reschedule children: {e}")

        obj_id = getattr(obj, 'id', None)
        console_logger.debug(f"[SAVE_VIEW] Save completed, object ID: {obj_id}")

        console_logger.debug(f"[SAVE_VIEW] Starting post-save hooks...")

        # Post-save hook or task
        post_hook_note = None
        post_hook = getattr(obj, 'post_save_hook', None)
        if callable(post_hook):
            console_logger.debug(f"[SAVE_VIEW] Executing custom post_save_hook...")
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
                console_logger.debug(f"[SAVE_VIEW] Custom post_save_hook completed")
            except Exception as e:
                console_logger.error(f"[SAVE_VIEW] Error in custom post_save_hook: {e}")
                post_hook_note = f'post_save_hook error: {e}'
        else:
            console_logger.debug(f"[SAVE_VIEW] No custom post_save_hook, checking Setting hooks...")
            # Execute save hooks from Setting records
            try:
                console_logger.debug(f"[SAVE_VIEW] Executing save_post hook from Settings...")
                from apps.core.constants.save_hooks import execute_save_hook
                hook_result = execute_save_hook(model_key, 'save_post', obj, data)
                console_logger.debug(f"[SAVE_VIEW] save_post hook result: {hook_result}")
                if not hook_result['success']:
                    post_hook_note = f'Post-save hook failed: {hook_result["errors"]}'
                    console_logger.warning(f"[SAVE_VIEW] Post-save hook failed: {post_hook_note}")
            except ImportError:
                console_logger.warning(f"[SAVE_VIEW] save_hooks module not available")
                pass  # Graceful degradation if save_hooks module not available
            except Exception as e:
                console_logger.error(f"[SAVE_VIEW] Error executing save_post hook: {e}")
                post_hook_note = f'Post-save hook error: {e}'

            console_logger.debug(f"[SAVE_VIEW] Checking for async save hooks...")
            # Execute save_async hooks asynchronously
            try:
                from apps.core.constants.save_hooks import get_save_hooks
                async_hooks = get_save_hooks(model_key)
                async_hook_found = False
                for hook_name, hook_data in async_hooks.items():
                    if 'save_async' in hook_data and hook_data['save_async']:
                        async_hook_found = True
                        break

                console_logger.debug(f"[SAVE_VIEW] Async hooks found: {async_hook_found}")
                if async_hook_found:
                    console_logger.info(f"[SAVE_VIEW] Executing execute_save_async_hooks...")
                    try:
                        from apps.core.tasks.cache_tasks import execute_save_async_hooks
                        if obj_id is not None:
                            console_logger.debug(f"[SAVE_VIEW] Calling execute_save_async_hooks with model={model_key}, id={obj_id}")
                            execute_save_async_hooks(model_key, obj_id, data)
                            console_logger.debug(f"[SAVE_VIEW] execute_save_async_hooks completed")
                    except ImportError:
                        console_logger.warning(f"[SAVE_VIEW] cache_tasks module not available")
                        pass  # Graceful degradation if tasks module not available
                    except Exception as e:
                        console_logger.error(f"[SAVE_VIEW] Error in execute_save_async_hooks: {e}")
                        post_hook_note = f'Async save hook error: {e}'
            except ImportError:
                console_logger.warning(f"[SAVE_VIEW] save_hooks module not available for async hooks")
                pass  # Graceful degradation if save_hooks module not available
            except Exception as e:
                console_logger.error(f"[SAVE_VIEW] Error checking async hooks: {e}")
                pass

        console_logger.debug(f"[SAVE_VIEW] Starting keyword updates...")
        # Update keywords synchronously so the response contains latest keywords
        try:
            update_keywords_method = getattr(obj, 'update_keywords', None)
            if update_keywords_method is not None and callable(update_keywords_method):
                console_logger.debug(f"[SAVE_VIEW] Executing update_keywords...")
                update_keywords_method()
                console_logger.debug(f"[SAVE_VIEW] update_keywords completed, doing keyword save...")
                obj.save(update_fields=['refs', 'metadata', 'version', 'dt_modified'])
                console_logger.debug(f"[SAVE_VIEW] Keyword save completed")
        except Exception as e:
            console_logger.error(f"[SAVE_VIEW] Error persisting deferred contact refs: {e}")
            logging.getLogger(__name__).exception('Error persisting deferred contact refs for %s id=%s', model_key, obj_id)

        # Persist deferred contact.refs (if earlier code marked them for deferred save)
        try:
            if contact and getattr(contact, '_refs_pending_save', False):
                links_bucket = bucket or ''
                current_links = contact.refs.get('links', {}) if isinstance(getattr(contact, 'refs', {}), dict) else {}
                bucket_links = current_links.get(links_bucket, []) if isinstance(current_links, dict) else []
                console_logger.debug(f"[SAVE_VIEW] Persisting deferred contact.refs for contact id={contact.pk} (links size={len(bucket_links)})")
                try:
                    contact.save(update_fields=['refs', 'version', 'dt_modified'])
                    contact.refresh_from_db()
                    try:
                        import json as _json
                        db_refs = contact.__class__.objects.filter(pk=contact.pk).values_list('refs', flat=True).first()
                        refreshed_links = contact.refs.get('links', {}) if isinstance(contact.refs, dict) else {}
                        refreshed_bucket = refreshed_links.get(links_bucket, []) if isinstance(refreshed_links, dict) else []
                        console_logger.debug(f"[SAVE_VIEW] Deferred contact saved; new version={getattr(contact,'version',None)} links_count={len(refreshed_bucket)} db_refs_preview={_json.dumps(db_refs)[:200] if db_refs else ''}")
                    except Exception:
                        refreshed_links = contact.refs.get('links', {}) if isinstance(contact.refs, dict) else {}
                        refreshed_bucket = refreshed_links.get(links_bucket, []) if isinstance(refreshed_links, dict) else []
                        console_logger.debug(f"[SAVE_VIEW] Deferred contact saved; new version={getattr(contact,'version',None)} links_count={len(refreshed_bucket)}")
                except Exception as e:
                    console_logger.error(f"[SAVE_VIEW] Error saving deferred contact refs: {e}")

                # Update obj.refs with contact link
                try:
                    from apps.core.services.save_contact_linking import link_obj_to_contact
                    if link_obj_to_contact(obj, contact):
                        obj.save(update_fields=['refs', 'version', 'dt_modified'])
                    from common.refs.links import ensure_bidirectional
                    ensure_bidirectional(contact, obj, kind='contact')
                except Exception:
                    pass
                try:
                    delattr(contact, '_refs_pending_save')
                except Exception:
                    pass
        except Exception as e:
            console_logger.error(f"[SAVE_VIEW] Failed to update keywords: {e}")
            logging.getLogger(__name__).exception('Failed to update keywords for %s id=%s', model_key, obj_id)

        console_logger.debug(f"[SAVE_VIEW] Generating response payload...")
        # this is needed to pass out to id of a new record
        try:
            safe_fields = [f.name for f in obj._meta.concrete_fields]
            record = model_to_dict(obj, fields=safe_fields)
            console_logger.debug(f"[SAVE_VIEW] Record dict generated with {len(record)} fields")
        except Exception as e:
            console_logger.warning(f"[SAVE_VIEW] Error generating record dict: {e}")
            record = {'id': getattr(obj, 'id', None)}
        payload = {
            'id': obj_id,
            'record': record,
            'model_name': model_key,
            'version': getattr(obj, 'version', None),
            'linked': linked
        }
        messages = []
        if field_size_errors:
            console_logger.debug(f"[SAVE_VIEW] Adding {len(field_size_errors)} field size errors to messages")
            messages.extend(field_size_errors)
        if post_hook_note:
            console_logger.debug(f"[SAVE_VIEW] Adding post hook note to messages: {post_hook_note}")
            messages.append(post_hook_note)
        if deprecation_flag:
            console_logger.debug(f"[SAVE_VIEW] Adding deprecation warning to messages")
            messages.append("'expected_version' is deprecated; use 'version' or If-Match header")
            logging.getLogger(__name__).warning("Deprecated expected_version field used in save payload for %s", model_key)
        if messages:
            payload['messages'] = messages
            console_logger.debug(f"[SAVE_VIEW] Response will include {len(messages)} messages")
        
        # ── Local-sync: queue async push to remote DB ────────────
        if obj_id is not None:
            try:
                from common.sync_tasks import dispatch_sync_to_remote
                sync_task_id = dispatch_sync_to_remote(model_key.lower(), obj_id)
                if sync_task_id:
                    payload['sync_task_id'] = sync_task_id
                    payload['sync_status'] = 'queued'
            except Exception:
                pass  # never block the response

        console_logger.info(f"[SAVE_VIEW] Returning successful response for {model_key} ID: {obj_id}")
        return api_response(data=payload)


class SaveWcapiViewWithModel(APIView):
    """
    WCAPI save view that accepts model_name in the URL path.
    Supports URLs like /wcapi/<model_name>/save or /wcapi/save/<model_name>
    """
    http_method_names = ["post", "options", "head"]

    def post(self, request, model_name=None, *args, **kwargs):
        # Get model_name from URL path, fallback to body if not provided
        if not model_name:
            # This shouldn't happen with proper URL routing, but defensive
            body = request.data or {}
            model_name = body.get('model_name') or body.get('model') or body.get('modelName')

        if not model_name:
            return api_response(
                data={"detail": "Missing required field: model_name (in URL or body)"},
                status=400
            )

        # Create a copy of request data and inject model_name
        data = dict(request.data or {})
        data['model_name'] = model_name

        # Create a mock request with the modified data
        from django.http import HttpRequest
        modified_request = HttpRequest()
        modified_request.method = request.method
        modified_request.META = request.META.copy()
        modified_request.GET = request.GET.copy()
        modified_request.POST = request.POST.copy()
        modified_request.COOKIES = request.COOKIES.copy()
        modified_request.session = request.session
        modified_request.user = request.user
        modified_request.data = data

        # Delegate to the main SaveWcapiView
        view_instance = SaveWcapiView()
        return view_instance.post(modified_request, *args, **kwargs)