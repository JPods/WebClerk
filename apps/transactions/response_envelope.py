"""Response envelope wrapper for consistent API metadata across transaction endpoints.

Provides mixins and utilities for wrapping all responses (list, detail, create, update)
with standardized metadata including request ID, timestamp, API version, and status info.
"""
from typing import Any, Dict, Optional
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status as http_status
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


class EnvelopeResponseMixin:
    """
    Mixin for ViewSets/Views to wrap responses with standardized envelope metadata.
    
    Wraps response data with:
    - request_id: unique request tracking ID
    - timestamp: ISO 8601 response timestamp
    - api_version: API version string
    - status: normalized status (success/fail/error)
    - code: HTTP status code
    """

    def finalize_response(self, request, response, *args, **kwargs):
        """Intercept response and wrap with envelope metadata."""
        response = super().finalize_response(request, response, *args, **kwargs)
        
        # Skip wrapping if already enveloped or if it's a redirect/stream
        if (
            getattr(response, '_api_enveloped', False) or
            getattr(response, 'streaming', False) or
            response.status_code in (301, 302, 304, 307, 308)
        ):
            return response

        # Extract or generate request ID
        request_id = request.META.get('HTTP_X_REQUEST_ID') or str(uuid4())
        
        # Build envelope metadata
        metadata = self._build_response_metadata(request, response, request_id)
        
        # Wrap the data payload
        if isinstance(response.data, dict):
            wrapped = {
                "meta": metadata,
                "data": response.data,
            }
        else:
            # Handle non-dict responses (e.g., list of items)
            wrapped = {
                "meta": metadata,
                "data": response.data,
            }

        response.data = wrapped
        response['X-Request-ID'] = request_id
        response['X-Response-Timestamp'] = metadata.get('timestamp', '')
        
        return response

    def _build_response_metadata(self, request, response, request_id: str) -> Dict[str, Any]:
        """Construct standardized response metadata."""
        http_status_code = response.status_code
        
        # Determine status category
        if http_status_code >= 500:
            status_str = 'error'
        elif http_status_code >= 400:
            status_str = 'fail'
        elif http_status_code >= 300:
            status_str = 'redirect'
        else:
            status_str = 'success'

        metadata = {
            "request_id": request_id,
            "timestamp": timezone.now().isoformat(),
            "api_version": getattr(self, 'api_version', '1.0'),
            "status": status_str,
            "code": http_status_code,
            "http_method": request.method,
            "path": request.path,
        }

        # Add count info if paginated list response
        if isinstance(response.data, dict) and 'results' in response.data:
            results = response.data.get('results', [])
            metadata['item_count'] = len(results) if isinstance(results, list) else 0
            if 'pagination' in response.data:
                metadata['pagination'] = response.data['pagination']

        return metadata


class TransactionViewSetMixin(EnvelopeResponseMixin):
    """
    Comprehensive ViewSet mixin for transaction endpoints.
    
    Combines envelope wrapping with common transaction API patterns:
    - Request/response logging
    - Standard error handling
    - Timestamp tracking
    - API version management
    """
    
    # Override in concrete ViewSet classes if needed
    api_version = "1.0"
    
    def get_exception_detail(self, exc) -> Dict[str, Any]:
        """Extract error detail from exception."""
        if hasattr(exc, 'detail'):
            return {"detail": str(exc.detail)}
        return {"detail": str(exc)}

    def handle_exception(self, exc):
        """Log exception with request context and wrap response."""
        logger.exception(
            f"Exception in {self.__class__.__name__}",
            extra={
                'path': self.request.path if hasattr(self, 'request') else 'N/A',
                'method': self.request.method if hasattr(self, 'request') else 'N/A',
            }
        )
        return super().handle_exception(exc)


class ListResponseEnvelopeMixin:
    """
    Mixin for list/retrieve responses to add consistent pagination metadata
    even when pagination is not explicitly requested.
    """
    
    def list(self, request, *args, **kwargs):
        """Wrap list response with pagination metadata."""
        response = super().list(request, *args, **kwargs)
        
        # Ensure pagination metadata exists in response
        if isinstance(response.data, dict) and 'pagination' not in response.data:
            # Add minimal pagination info if not present
            results = response.data.get('results', response.data)
            if isinstance(results, list):
                response.data['pagination'] = {
                    'page': 1,
                    'page_size': len(results),
                    'total_items': len(results),
                    'total_pages': 1,
                }
        
        return response


def wrap_error_response(
    *,
    message: str,
    status_code: int = http_status.HTTP_400_BAD_REQUEST,
    error_code: Optional[str] = None,
    details: Optional[Any] = None,
    request_id: Optional[str] = None,
) -> Response:
    """
    Construct a standardized error response envelope.
    
    Example:
        return wrap_error_response(
            message="Invalid proposal status",
            status_code=400,
            error_code="INVALID_STATUS",
            details={"current_status": "canceled"},
        )
    """
    request_id = request_id or str(uuid4())
    
    error_payload = {
        "code": error_code or "UNKNOWN_ERROR",
        "message": message,
    }
    if details is not None:
        error_payload["details"] = details

    envelope = {
        "meta": {
            "request_id": request_id,
            "timestamp": timezone.now().isoformat(),
            "status": "fail" if 400 <= status_code < 500 else "error",
            "code": status_code,
        },
        "error": error_payload,
        "data": None,
    }

    response = Response(envelope, status=status_code)
    response['X-Request-ID'] = request_id
    return response
