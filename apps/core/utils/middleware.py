"""
JSON-only middleware for WCAPI endpoints.

This middleware enforces JSON-only responses and requests for WCAPI endpoints.
"""

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


class JSONOnlyMiddleware(MiddlewareMixin):
    """
    Middleware to enforce JSON-only responses for WCAPI endpoints.
    
    This middleware can be used to ensure that WCAPI endpoints only accept
    and return JSON data.
    """
    EXEMPT_PATHS = (
        '/api/schema/',
        '/api/swagger/',
        '/api/redoc/',
    )
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(request.path.startswith(p) for p in self.EXEMPT_PATHS):
            return self.get_response(request)
        # Check if this is a WCAPI endpoint
        if hasattr(request, 'path') and request.path.startswith('/wcapi/'):
            # Enforce JSON content type for requests
            if request.method in ['POST', 'PUT', 'PATCH']:
                content_type = request.META.get('CONTENT_TYPE', '')
                if 'application/json' not in content_type:
                    return JsonResponse({
                        'error': 'WCAPI endpoints only accept JSON content'
                    }, status=400)
        
        response = self.get_response(request)
        return response