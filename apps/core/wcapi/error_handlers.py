from django.http import JsonResponse
from typing import Any

def _json_error(request, status: int, message: str, extra: dict[str, Any] | None = None):
    payload = {"ok": False, "code": status, "message": message}
    if extra:
        payload.update(extra)
    return JsonResponse(payload, status=status, json_dumps_params={"ensure_ascii": False})

def json_bad_request(request, exception=None):
    return _json_error(request, 400, "Bad Request")

def json_permission_denied(request, exception=None):
    return _json_error(request, 403, "Forbidden")

def json_not_found(request, exception=None):
    return _json_error(request, 404, "Not Found")

def json_server_error(request, exception=None):
    return _json_error(request, 500, "Server Error")