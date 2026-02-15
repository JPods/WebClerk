"""
Middleware package — re-exports for settings.MIDDLEWARE compatibility.

All middleware classes are importable from ``common.middleware`` exactly
as before; only the internal layout has changed.

Active middleware (listed in settings.MIDDLEWARE):
  - RequestLogMiddleware       — request/response logging + X-Request-ID
  - AutoEnvelopeMiddleware     — wraps JSON responses in ApiEnvelope
  - ExceptionAsJsonMiddleware  — converts unhandled exceptions to JSON
  - EnsureRenderedMiddleware   — renders DRF/Template responses early
  - WriteGateMiddleware        — blocks unsafe writes on non-whitelisted paths

Shared helpers are in ``common.middleware.helpers``.
"""

from common.middleware.logging import RequestLogMiddleware
from common.middleware.envelope import AutoEnvelopeMiddleware
from common.middleware.exceptions import ExceptionAsJsonMiddleware
from common.middleware.rendering import EnsureRenderedMiddleware
from common.middleware.security import WriteGateMiddleware
from common.middleware.helpers import ENVELOPE_SKIPS  # noqa: F401 – used by tests

__all__ = [
    "RequestLogMiddleware",
    "AutoEnvelopeMiddleware",
    "ExceptionAsJsonMiddleware",
    "EnsureRenderedMiddleware",
    "WriteGateMiddleware",
    "ENVELOPE_SKIPS",
]
