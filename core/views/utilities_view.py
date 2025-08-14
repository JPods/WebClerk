from django.http import JsonResponse
from django.views import View
from core.services.access_fields import get_allowed_fields

class AllowedFieldsView(View):
    def get(self, request):
        table = request.GET.get("table")
        role = request.GET.get("role")
        access_type = request.GET.get("access_type", "view")
        if not table or not role:
            return JsonResponse({"success": False, "error": "table and role required"}, status=400)
        fields = get_allowed_fields(table, role, access_type)
        return JsonResponse({"success": True, "fields": fields})