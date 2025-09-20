from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def api_exception_handler(exc, context):
    """
    Wrap DRF's handler to guarantee JSON structure for all errors.
    """
    resp = exception_handler(exc, context)
    if resp is None:
        # Non-DRF exceptions: generic JSON envelope
        return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    # Ensure standard envelope and JSON content type
    data = resp.data
    if not isinstance(data, dict) or "detail" not in data:
        data = {"detail": data}
    return Response(data, status=resp.status_code, headers=resp.headers)