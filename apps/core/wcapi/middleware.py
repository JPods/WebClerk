from http import HTTPStatus
from typing import Callable
from django.http import JsonResponse, HttpRequest, HttpResponse

API_PREFIXES = ("/api/", "/wcapi/", "/document/", "/actions/", "/readme", "/tag/", "/template", "/pending")

def _status_message(code: int) -> str:
    try:
        return HTTPStatus(code).phrase
    except Exception:
        return "Error"

class JSONOnlyMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        resp = self.get_response(request)
        return self._coerce_json(request, resp)

    def _wants_json(self, request: HttpRequest) -> bool:
        if request.path.startswith(API_PREFIXES):
            return True
        accept = request.META.get("HTTP_ACCEPT", "")
        content_type = request.META.get("CONTENT_TYPE", "")
        return ("application/json" in accept) or ("application/json" in content_type)

    def _coerce_json(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        if "application/json" in response.headers.get("Content-Type", ""):
            return response
        if not self._wants_json(request):
            return response
        if response.status_code < 400:
            return response
        payload = {"ok": False, "code": response.status_code, "message": _status_message(response.status_code), "path": request.path}
        return JsonResponse(payload, status=response.status_code)