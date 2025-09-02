# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/views/utilities_view.py
from django.http import JsonResponse  # legacy
from common.api_responses import api_response
"""
This module defines a Django view for retrieving allowed fields for a given table, role, and access type.

Classes:
    AllowedFieldsView(View): Handles GET requests to return the list of allowed fields for a specified table and role.

Methods:
    AllowedFieldsView.get(request):
        Handles GET requests. Expects 'table' and 'role' as query parameters, and optionally 'access_type' (defaults to 'view').
        Returns a JSON response with the allowed fields or an error if required parameters are missing.
"""
from django.views import View
from apps.core.services.view_edit_access import get_view_edit_fields

class AllowedFieldsView(View):
    def get(self, request):
        table = request.GET.get("table")
        role = request.GET.get("role")
        access_type = request.GET.get("access_type", "view")
        if not table or not role:
            return api_response(success=False, status_code=400, message='table and role required', error={'code':'missing_params','details':'table and role required'})
        fields = get_view_edit_fields(table, role, access_type)
        return api_response(data={'table': table, 'role': role, 'access_type': access_type, 'fields': fields})