"""Unified API response helpers.

This module defines a single public helper `api_response` which wraps
payloads in a consistent envelope used by modernized DRF endpoints.

Envelope Shape:

{
  "status": "success" | "error",
  "message": "optional human readable string",
  "data": object | list | null,
  "error": { "code": str, "details": any } | null,
  "meta": { arbitrary metadata such as pagination } | null
}

Rules:
* Omit keys (message, data, error, meta) when they are None/empty to keep responses lean.
* `status` is always present.
* HTTP success codes (2xx) should use status="success"; 4xx/5xx should prefer status="error".
* Pagination meta keys (if present): total, page, page_size, pages, next, previous.

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
    meta: Optional[Dict[str, Any]] = None,
    raw: bool = False,
) -> Response:
    """Return a DRF Response with the unified envelope.

    Set `raw=True` to bypass wrapping (used when a view detects `?raw=1`).
    """
    if raw:
        # Caller explicitly wants unwrapped data (transitional).
        return Response(data, status=status_code)

    payload: Dict[str, Any] = {"status": "success" if success else "error"}
    if message:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    if error is not None:
        payload["error"] = error
    if meta:
        payload["meta"] = meta
    return Response(payload, status=status_code)
