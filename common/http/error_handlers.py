from __future__ import annotations
from django.http import HttpRequest, JsonResponse

def handler404_json(request: HttpRequest, exception=None):
    # Standardized envelope for not found
    payload = {
        "status": "fail",
        "message": "Not found",
        "data": None,
        "error": {"code": "not_found"},
    }
    return JsonResponse(payload, status=404)