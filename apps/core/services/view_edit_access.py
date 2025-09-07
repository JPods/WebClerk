# Used by celery to load view/edit fields from the Setting model
# This module provides utilities for managing and enforcing view/edit access to model fields
# based on user roles and model names, using configuration stored in the Setting model.

# Functions:

# - get_view_edit_fields(model_name: str, role: str, access_type: str = "view") -> list:
#     Retrieves a list of allowed fields for a specified model, user role, and access type
#     ('view' or 'edit'), based on the active Setting record.

# - filter_json_response(model_name_getter, access_type="view"):
#     Decorator for Django views that filters the JSON response data, ensuring only fields
#     permitted for the user's role and access type are included in the response.

# - get_allowed_fields(model_name: str, role: str, access_type: str = "view"):
#     Alias for get_view_edit_fields, returns the list of allowed fields for the given parameters.

# - filter_record_for_role(record: dict, model_name: str, role: str, access_type: str = "view"):
#     Filters a dictionary record, returning only the fields allowed for the specified model,
#     role, and access type.

# Usage:
# - Use these utilities to enforce field-level permissions in API responses or business logic,
#   ensuring users only see or edit fields they are authorized for.

from apps.core.models import Setting
import json
import os
import logging
from functools import wraps
from django.http import JsonResponse
from django.apps import apps as _apps

def dev_bypass_enabled() -> bool:
    """Evaluate bypass flag dynamically each call (avoid import‑time caching)."""
    return os.getenv('VIEW_EDIT_DEV_BYPASS', '0') == '1'

_reported_missing: set[tuple[str,str,str]] = set()
logger = logging.getLogger(__name__)

def get_view_edit_fields(model_name: str, role: str, access_type: str = "view") -> list:
    """
    Returns a list of allowed fields for a given model key, role, and access_type ('view' or 'edit'),
    using Setting records from the database.
    """
    if dev_bypass_enabled():
        # Wide open: simply signal '*' (all fields) – no model resolution needed.
        return ['*']
    try:
        setting = Setting.objects.filter(
            is_active=True,
            purpose="view_edit",
            model_name=model_name
        ).first()
        data = getattr(setting, "data", None)
    # Intentionally silent unless debugging; uncomment for deep trace.
        if not isinstance(data, dict):
            return []
        role_data = data.get(role.upper())
        if not role_data:
            role_data = data.get("PUBLIC", {})
            # fallback to PUBLIC already handled; avoid noisy prints
        return role_data.get(access_type, [])
    # unreachable after return
    except Exception:
        key = (model_name, role.upper(), access_type)
        if key not in _reported_missing:
            _reported_missing.add(key)
            logger.debug("view_edit_access: no Setting found (model=%s role=%s access=%s) - returning empty list (may be widened by bypass/fail-open)", *key)
        return []
        

def filter_json_response(model_name_getter, access_type="view"):
    """
    Decorator to filter JSON response data for allowed fields.
    model_name_getter: function(request, *args, **kwargs) -> str
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(self, request, *args, **kwargs):
            response = view_func(self, request, *args, **kwargs)
            if isinstance(response, JsonResponse):
                data = json.loads(response.content)
                if "data" in data:
                    include_related = False
                    if request.method == "GET":
                        include_related = request.GET.get("include_related", "false").lower() == "true"
                    elif request.method in ["POST", "PUT"]:
                        try:
                            body = json.loads(request.body)
                            include_related = body.get("include_related", False)
                        except Exception:
                            pass
                    if include_related and "related" in data:
                        user_role = getattr(request.user, "role", "PUBLIC")
                        model_name = model_name_getter(request, *args, **kwargs)
                        from apps.core.services.view_edit_access import filter_record_for_role
                        # data["related"] should be a dict of lists keyed by model name
                        filtered_related = {}
                        for rel_model_name, records in data["related"].items():
                            filtered_related[rel_model_name] = [
                                filter_record_for_role(r, rel_model_name, user_role, access_type)
                                for r in records
                            ]
                        data["related"] = filtered_related
                    response = JsonResponse(data)
            return response
        return _wrapped_view
    return decorator

def get_allowed_fields(model_name: str, role: str, access_type: str = "view"):
    return get_view_edit_fields(model_name, role, access_type)

def filter_record_for_role(record: dict, model_name: str, role: str, access_type: str = "view"):
    allowed_fields = get_allowed_fields(model_name, role, access_type)
    # If wildcard or bypass -> expand to model concrete fields to ensure full dict
    if '*' in allowed_fields or dev_bypass_enabled() or not allowed_fields:
        # Attempt to resolve the Django model by class name only.
        model = None
        for m in _apps.get_models():
            if m.__name__.lower() == model_name.lower():
                model = m
                break
        if model is not None:
            field_names = [f.name for f in model._meta.get_fields() if getattr(f, 'concrete', False) and not getattr(f, 'many_to_many', False)]  # type: ignore[attr-defined]
            # Include any existing keys (JSON / dynamic) to avoid dropping data
            for k in record.keys():
                if k not in field_names:
                    field_names.append(k)
            return {k: record.get(k) for k in field_names}
        # fallback just return record untouched
        return record
    return {k: v for k, v in record.items() if k in allowed_fields}

