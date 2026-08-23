"""Custom DRF exception handler producing standardized envelope.

Maps common DRF + Django exceptions to stable error.code values while preserving
HTTP status codes. All API errors (4xx/5xx) should return:

{
    "status": "fail" | "error",  # fail for 4xx, error for 5xx
    "message": <short human message>,
    "error": { "code": <machine_code>, "details": <original detail> }
}
"""
from __future__ import annotations

from typing import Any
from rest_framework.views import exception_handler as drf_default_handler
from rest_framework.response import Response
from rest_framework import status as drf_status, exceptions as drf_exc
from django.core.exceptions import PermissionDenied
from django.http import Http404
from common.api_responses import api_response

CODE_MAP = {
    drf_exc.ValidationError: 'validation_error',
    drf_exc.NotAuthenticated: 'not_authenticated',
    drf_exc.AuthenticationFailed: 'auth_failed',
    drf_exc.PermissionDenied: 'forbidden',
    PermissionDenied: 'forbidden',
    drf_exc.NotFound: 'not_found',
    Http404: 'not_found',
    drf_exc.MethodNotAllowed: 'method_not_allowed',
    drf_exc.NotAcceptable: 'not_acceptable',
    drf_exc.UnsupportedMediaType: 'unsupported_media_type',
    drf_exc.Throttled: 'throttled',
    drf_exc.ParseError: 'parse_error',
}

def _code_for(exc: Exception) -> str:
    for cls, code in CODE_MAP.items():
        if isinstance(exc, cls):
            return code
    return 'error'

def api_exception_handler(exc: Exception, context: dict[str, Any]):
    """Return unified envelope for exceptions.

    Falls back to default DRF formatting for details, then wraps.
    """
    response = drf_default_handler(exc, context)
    if response is None:  # non-DRF error -> generic 500
        return api_response(success=False, status_code=500, message='Server error', error={'code': 'server_error', 'details': str(exc)})
    # Use DRF's generated status + data for detail
    detail = response.data
    # DRF detail may be a string or dict (field errors). Canonicalize to:
    #   error: { code, details: <dict|list|str> }
    message = 'Error'
    structured = detail
    if isinstance(detail, dict) and 'detail' in detail and isinstance(detail['detail'], str) and len(detail) == 1:
        # Simple {'detail': '...'}; treat as message (do not duplicate into details unless needed)
        message = detail['detail']
        structured = detail['detail']
    elif isinstance(detail, dict):
        if 'detail' in detail and isinstance(detail['detail'], str):
            message = detail['detail']
    code = _code_for(exc)
    error_block = {'code': code, 'details': structured}
    resp_obj = api_response(success=False, status_code=response.status_code, message=message, error=error_block)
    # Backwards compatibility: bubble field keys onto top-level envelope (Response.data['field'])
    # No legacy bubbling; field errors remain in error.details
    return resp_obj
