from django.http import JsonResponse
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from rest_framework.views import APIView

class JsonMethodNotAllowedMixin:
    """
    Ensures 405 responses are JSON (rendered), not TemplateResponse.
    Attach to API views that may not implement certain verbs.
    """
    def http_method_not_allowed(self, request, *args, **kwargs):
        return JsonResponse({"detail": f"Method '{request.method}' not allowed."}, status=405)

class BaseJSONAPIView(APIView):
    """
    DRF APIView locked to JSON-only IO.
    """
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser]

class OptimisticGetOnPatchMixin:
    """
    Accept PATCH as a no-op read for optimistic clients (returns GET payload).
    Also forces DRF authentication by touching request.user.
    """
    def patch(self, request, *args, **kwargs):
        _ = request.user  # force DRF perform_authentication
        get = getattr(self, "get", None)
        if callable(get):
            return get(request, *args, **kwargs)
        return JsonResponse({"detail": "OK"}, status=200)