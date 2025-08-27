# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/services/view_edit_access.py
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

from apps.core.models import Setting
import json
from functools import wraps
from django.http import JsonResponse

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
        data = getattr(setting, "data", None)
        #print(f"get_view_edit_fields: table={table_name}, role={role}, access_type={access_type}, data={data}") 
        if not isinstance(data, dict):
            return []
        role_data = data.get(role.upper())
        if not role_data:
            role_data = data.get("PUBLIC", {})
            print (f"1get_view_edit_fields result: role_data={role_data}")
        return role_data.get(access_type, [])
        print (f"2get_view_edit_fields result: role_data={role_data}")
    except Setting.DoesNotExist:
        print(f"3get_view_edit_fields error: table={table_name}, role={role}, access_type={access_type}, data=Setting.DoesNotExist")
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
                        table_name = table_name_getter(request, *args, **kwargs)
                        from apps.core.services.view_edit_access import filter_record_for_role
                        # data["related"] should be a dict of lists keyed by table name
                        filtered_related = {}
                        for table, records in data["related"].items():
                            filtered_related[table] = [
                                filter_record_for_role(r, table, user_role, access_type)
                                for r in records
                            ]
                        data["related"] = filtered_related
                    response = JsonResponse(data)
            return response
        return _wrapped_view
    return decorator

def get_allowed_fields(table_name: str, role: str, access_type: str = "view"):
    return get_view_edit_fields(table_name, role, access_type)

def filter_record_for_role(record: dict, table_name: str, role: str, access_type: str = "view"):
    allowed_fields = get_allowed_fields(table_name, role, access_type)
    return {k: v for k, v in record.items() if k in allowed_fields}

