# Used by celery to load view/edit fields from the Setting model
# This module provides utilities for managing and enforcing view/edit access to model fields
# based on user roles and table names, using configuration stored in the Setting model.

# Functions:

# - get_view_edit_fields(table_name: str, role: str, access_type: str = "view") -> list:
#     Retrieves a list of allowed fields for a specified table, user role, and access type
#     ('view' or 'edit'), based on the active Setting record.

# - filter_json_response(table_name_getter, access_type="view"):
#     Decorator for Django views that filters the JSON response data, ensuring only fields
#     permitted for the user's role and access type are included in the response.

# - get_allowed_fields(table_name: str, role: str, access_type: str = "view"):
#     Alias for get_view_edit_fields, returns the list of allowed fields for the given parameters.

# - filter_record_for_role(record: dict, table_name: str, role: str, access_type: str = "view"):
#     Filters a dictionary record, returning only the fields allowed for the specified table,
#     role, and access type.

# Usage:
# - Use these utilities to enforce field-level permissions in API responses or business logic,
#   ensuring users only see or edit fields they are authorized for.

from core.models import Setting
import json
from functools import wraps

def get_view_edit_fields(table_name: str, role: str, access_type: str = "view") -> list:
    """
    Returns a list of allowed fields for a given table, role, and access_type ('view' or 'edit'),
    using Setting records from the database.
    """
    try:
        setting = Setting.objects.get(
            is_active=True,
            purpose="view_edit",
            table_name=table_name
        )
        role_data = setting.data.get(role.upper())
        if not role_data:
            role_data = setting.data.get("PUBLIC", {})
        return role_data.get(access_type, [])
    except Setting.DoesNotExist:
        return []

def filter_json_response(table_name_getter, access_type="view"):
    """
    Decorator to filter JSON response data for allowed fields.
    table_name_getter: function(request, *args, **kwargs) -> str
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(self, request, *args, **kwargs):
            response = view_func(self, request, *args, **kwargs)
            # Only filter if response is a JsonResponse and has 'data'
            if isinstance(response, JsonResponse):
                # Parse the response content
                data = json.loads(response.content)
                if "data" in data:
                    user_role = getattr(request.user, "role", "PUBLIC")
                    table_name = table_name_getter(request, *args, **kwargs)
                    from core.services.view_edit_access import filter_record_for_role
                    filtered = [filter_record_for_role(r, table_name, user_role, access_type) for r in data["data"]]
                    data["data"] = filtered
                    response.content = json.dumps(data)
            return response
        return _wrapped_view
    return decorator

def get_allowed_fields(table_name: str, role: str, access_type: str = "view"):
    return get_view_edit_fields(table_name, role, access_type)

def filter_record_for_role(record: dict, table_name: str, role: str, access_type: str = "view"):
    allowed_fields = get_allowed_fields(table_name, role, access_type)
    return {k: v for k, v in record.items() if k in allowed_fields}

