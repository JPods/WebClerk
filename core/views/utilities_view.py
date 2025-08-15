from django.http import JsonResponse
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
from core.services.view_edit_access import get_view_edit_fields

class AllowedFieldsView(View):
    def get(self, request):
        table = request.GET.get("table")
        role = request.GET.get("role")
        access_type = request.GET.get("access_type", "view")
        if not table or not role:
            return JsonResponse({"success": False, "error": "table and role required"}, status=400)
        fields = get_view_edit_fields(table, role, access_type)
        return JsonResponse({"success": True, "fields": fields})