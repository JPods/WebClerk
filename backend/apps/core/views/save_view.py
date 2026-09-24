# path: apps/core/views/save_view.py
from common.api_responses import api_response
from common.write_through import is_write_through, forward_and_store
from django.conf import settings
import logging
from apps.core.services.save import (Actor, Refused, STAFF_ONLY_MODELS,
                                     TRANSACTION_LINE_MODELS, resolve_model,
                                     save_record)

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
from django.core.exceptions import ValidationError as DjangoValidationError
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


def deep_merge_dict(a: dict, b: dict, _depth: int = 0) -> dict:
    """Recursively merge dict b into dict a (in place) and return a.
    - protects dictionary structures
    - If a[key] and b[key] are both dicts, merge recursively.
    - Otherwise, b[key] overwrites a[key].
    - Raises ValueError if depth exceeds 8 levels (prevents stack overflow).
    """
    if _depth >= 8:
        raise ValueError("JSON merge depth exceeds 8 levels")
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            deep_merge_dict(a[k], v, _depth + 1)
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


# These live with the door that enforces them (core/services/save.py).
_STAFF_ONLY_MODELS = STAFF_ONLY_MODELS
_TRANSACTION_LINE_MODELS = TRANSACTION_LINE_MODELS

_CONTACT_AUTHORITY_FIELDS = ('is_superuser', 'is_staff', 'is_active', 'role', 'groups',
                             'user_permissions', 'refs', 'metadata')
# Both the column and the FK alias: assign_fields writes customer_id from key "customer".
_CONTACT_SCOPE_FIELDS = ('customer_id', 'vendor_id', 'rep_id', 'manufacturer_id', 'is_employee',
                         'customer', 'vendor', 'rep', 'manufacturer')


def _key_root(key):
    """Root model field a save key targets: "refs.roles" and "is_superuser[x=y]" -> "refs"/"is_superuser".

    The guard compares against model fields, but the save pipeline accepts dot-paths
    and array selectors. Comparing raw keys let "refs.roles" and selector keys slip
    past every check (adversarial review 2026-09-15).
    """
    if not isinstance(key, str):
        return key
    root = key.split('.', 1)[0]
    return root.split('[', 1)[0]


def _setting_edit_warning(user, model_key: str, obj):
    """Coach a superuser editing a Setting. Returns a message, or None.

    Bill, 2026-09-20: *"let's allow setting records to be edited by superusers. If a
    superuser does harm, there are so many ways possible that we cannot stop."* And:
    *"Alice should warn superusers that they are messing with their core with modifying
    settings and that the record and pydantic must be aligned."*

    So the permission is granted and the warning is not optional. Two things are worth
    saying, and the second is the one that bites later:

    1. Settings are the core. Layouts, access enumerations and model definitions all live
       here, so a bad edit does not fail where it was made.
    2. **The record and its Pydantic schema must stay aligned.** A Setting's ``config`` is
       validated against a schema in code; changing the record without moving the schema
       (or the reverse) is drift that surfaces somewhere else, as something else's bug.
       Behaviours belong in the schema, not the record.

    Alice keeps the observation so repeats reach WC_HQ rather than being read once and
    forgotten — coach, don't drop.
    """
    if model_key != 'setting':
        return None
    if not (user and getattr(user, 'is_authenticated', False) and user.is_superuser):
        return None

    warning = (
        "You are editing core configuration. Settings drive layouts, access and model "
        "definitions, so a mistake here surfaces elsewhere. The record and its Pydantic "
        "schema must stay aligned — change one without the other and they drift."
    )
    try:
        from apps.ai_assistant.services.notes import create_note
        create_note(
            "log",
            role="user_interaction",
            name="superuser edited a Setting",
            parent_model="setting",
            details={
                "setting_id": getattr(obj, 'pk', None),
                "purpose": getattr(obj, 'purpose', None),
                "parent_model": getattr(obj, 'parent_model', None),
                "user_id": getattr(user, 'pk', None),
                "source": "wcapi.save",
                "warning": warning,
            },
        )
    except Exception:
        console_logger.exception("[SAVE_VIEW] Failed to write alice_log for Setting edit")
    return warning


def _contact_account_denial(user, obj, data, is_update):
    """Return the name of the first contact field this user may not change, else None.

    Admins (superuser, or own role admin — not is_staff) are unrestricted. Everyone else:
      - password: own contact only (never set on create — accounts come from signup)
      - email: may be set on a new contact; changed only on their own contact
      - privilege fields: never
      - org scope fields: never on their own contact (prevents self re-homing into another org)
    """
    from apps.core.services.access import own_role
    # Admin is superuser or an own role of admin — not is_staff (Bill, 2026-09-23).
    if user and getattr(user, 'is_authenticated', False) and (
            user.is_superuser or own_role(user) == 'admin'):
        return None
    data = data or {}
    roots = {_key_root(k): k for k in data.keys()}
    is_self = bool(is_update and user and getattr(obj, 'pk', None) is not None and obj.pk == getattr(user, 'pk', None))
    for field in _CONTACT_AUTHORITY_FIELDS:
        if field in roots:
            return roots[field]
    if not is_self:
        if 'password' in roots:
            return roots['password']
        if is_update and 'email' in roots and (data.get('email') or '') != (getattr(obj, 'email', '') or ''):
            return roots['email']
    # Org scope is authority, not a preference: it decides what the account can see.
    # Checked on every path — own record, someone else's, and on create — because
    # re-homing another contact or pre-provisioning one inside an org is the same
    # escalation by a different route.
    for field in _CONTACT_SCOPE_FIELDS:
        if field in roots and data.get(roots[field]) != getattr(obj, field, None):
            return roots[field]
    return None

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

        # Query parameters are the HTTP layer's business: fold them into the payload
        # before the door sees it.
        if not data.get('model_name') and request.query_params.get('model_name'):
            data['model_name'] = request.query_params.get('model_name')
        if data.get('id') is None and request.query_params.get('id') is not None:
            data['id'] = request.query_params.get('id')
        data['id'] = coerce_int(data.get('id'))

        # ── Write-through: forward to remote, store bundle locally ──
        if is_write_through():
            model_cls = None
            try:
                model_cls, _key, _norm = resolve_model(data.get('model_name') or '')
            except Refused as refused:
                return api_response(success=False, status_code=refused.status,
                                    message=refused.message, error=refused.as_error())
            console_logger.info("[SAVE_VIEW] Write-through mode — forwarding save to remote DB")
            wt_payload, wt_status = forward_and_store(request, model_cls, data)
            if wt_status >= 400:
                return api_response(
                    success=False, status_code=wt_status,
                    message=wt_payload.get('detail', 'Write-through failed'),
                    error={'code': 'write_through_error', 'details': wt_payload},
                )
            return api_response(data=wt_payload, status_code=wt_status)

        # ── The door ──
        # Everything a save does lives in core/services/save.py, so a command, a sync
        # bundle or the admin reaches the same authorization, validation, hooks and
        # version check as this endpoint (Bill, 2026-09-22: one door, no backdoor).
        try:
            result = save_record(
                Actor.from_request(request),
                data,
                record_id=coerce_int(data.get('id')),
                expected_version=coerce_int(data.get('version')),
            )
        except Refused as refused:
            console_logger.info("[SAVE_VIEW] Refused (%s): %s", refused.code, refused.message)
            return api_response(success=False, status_code=refused.status,
                                message=refused.message, error=refused.as_error())
        except IntegrityError as e:
            console_logger.error(f"[SAVE_VIEW] Integrity error during save: {e}")
            return api_response(success=False, status_code=400, message='Integrity error', error={'code':'integrity_error','details': str(e)})
        except ValueError as e:
            console_logger.error(f"[SAVE_VIEW] Value error during save: {e}")
            return api_response(success=False, status_code=400, message='Invalid field values', error={'code':'invalid_field','details': str(e)})
        except Exception as e:
            console_logger.error(f"[SAVE_VIEW] Exception during save: {e}")
            return api_response(success=False, status_code=500, message='Failed to save', error={'code':'save_failed','details': str(e)})

        return api_response(data=result.payload(), message=result.warning)


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