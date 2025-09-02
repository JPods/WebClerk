"""Unified API response helpers.

This module defines a single public helper `api_response` which wraps
payloads in a consistent envelope used by modernized DRF endpoints.

Envelope Shape (2025-09-02):

{
    "status": "success" | "fail" | "error",   # success for 2xx, fail for 4xx, error for 5xx
    "error": null | { "code": str, "details": any },
    "code": int,                                # HTTP status code mirrored
    "message": str,                             # always present ("" if not set)
    "data": object | list | null                # application payload
}

Notes:
* Pagination or other metadata should be embedded inside data (e.g. {"results": [...], "page":1, ...}).
* Keys are always present except error (null on success/fail when no error block needed) and data (set to null if omitted).
* This supersedes prior envelope that used meta and omitted null fields.

Transitional Opt-Out:
Endpoints may honor a `?raw=1` query parameter to bypass the envelope for
legacy clients while migration is in progress.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from rest_framework.response import Response

__all__ = ["api_response"]


def api_response(
    *,
    data: Any = None,
    message: Optional[str] = None,
    success: bool = True,
    status_code: int = 200,
    error: Optional[Dict[str, Any]] = None,
    raw: bool = False,
) -> Response:
    """Return a DRF Response with the new strict envelope.

    raw=True returns the underlying data only (escape hatch for rare cases).
    """
    if raw:
        return Response(data, status=status_code)

    if status_code >= 500:
        status_str = 'error'
    elif status_code >= 400:
        status_str = 'fail'
    else:
        status_str = 'success'

    payload: Dict[str, Any] = {
        'status': status_str,
        'error': error if error is not None else None,
        'code': status_code,
        'message': message or '',
        'data': data if data is not None else None,
    }
    return Response(payload, status=status_code)
