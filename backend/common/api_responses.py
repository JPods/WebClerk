"""Unified API response helpers.

Public helpers in this module standardize API payloads into the canonical
``ApiEnvelope`` shape used across the platform.

Envelope Shape (2025-12-02):

```
{
        "status": "success" | "fail" | "error",  # derived from HTTP code buckets
        "code": int,                                # mirrors HTTP status
        "message": str,                             # human readable summary ("" allowed)
        "data": object | list | null,               # application payload
        "error": null | {"code": str, "details": any}
}
```

Notes:
* Pagination/metadata should live under ``data`` (e.g. ``{"results": [...], "total": 100}``).
* ``error`` is optional. For non-2xx responses, callers may populate it with a
    structured payload (code + details).
* ``message`` is always present (empty string if omitted) to simplify client
    rendering logic.

"""
from __future__ import annotations

from typing import Any, Dict, Optional
from rest_framework.response import Response

__all__ = ["api_response", "build_api_envelope"]


def build_api_envelope(
    *,
    data: Any = None,
    message: Optional[str] = None,
    status_code: int = 200,
    error: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Construct the canonical API envelope payload without instantiating a Response."""
    if status_code >= 500:
        status_str = 'error'
    elif status_code >= 400:
        status_str = 'fail'
    else:
        status_str = 'success'

    return {
        'status': status_str,
        'error': error if error is not None else None,
        'code': status_code,
        'message': message or '',
        'data': data if data is not None else None,
    }


def api_response(
    *,
    data: Any = None,
    message: Optional[str] = None,
    success: bool = True,
    status_code: int = 200,
    error: Optional[Dict[str, Any]] = None,
    error_code: Optional[str] = None,
) -> Response:
    """Return a DRF Response with the new strict envelope.
    """
    if error_code and error is None:
        error = {"code": error_code, "details": None}
    elif error_code and error is not None:
        error.setdefault("code", error_code)
    payload = build_api_envelope(data=data, message=message, status_code=status_code, error=error)
    resp = Response(payload, status=status_code)
    setattr(resp, '_api_enveloped', True)
    return resp
