"""ExceptionAsJsonMiddleware — converts unhandled exceptions to JSON for API clients."""
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from common.middleware.helpers import is_template_page


class ExceptionAsJsonMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):  # pragma: no cover (exercised via integration)
        try:
            path = getattr(request, 'path', '')
            accept = request.headers.get('Accept', '') if hasattr(request, 'headers') else ''
            content_type = request.headers.get('Content-Type', '') if hasattr(request, 'headers') else ''
            wants_json = ('application/json' in accept) or ('application/json' in content_type)
            # Treat any non-template endpoint as API when JSON-by-default is enabled
            json_default = bool(getattr(settings, 'API_JSON_DEFAULT', True))
            if is_template_page(path) and not wants_json:
                return None

            from django.core.exceptions import PermissionDenied
            from django.http import Http404, JsonResponse
            from rest_framework import exceptions as drf_exc

            status_code = 500
            code = 'server_error'
            message = 'Server error'
            if isinstance(exception, (Http404, drf_exc.NotFound)):
                status_code, code, message = 404, 'not_found', 'Not found'
            elif isinstance(exception, (PermissionDenied, drf_exc.PermissionDenied)):
                status_code, code, message = 403, 'forbidden', 'Forbidden'
            elif isinstance(exception, (drf_exc.NotAuthenticated, drf_exc.AuthenticationFailed)):
                status_code, code, message = 401, 'not_authenticated', 'Authentication required'
            elif isinstance(exception, drf_exc.MethodNotAllowed):
                status_code, code, message = 405, 'method_not_allowed', 'Method not allowed'
            elif isinstance(exception, drf_exc.ParseError):
                status_code, code, message = 400, 'parse_error', 'Invalid request'

            details = str(exception) if getattr(settings, 'DEBUG', False) else None
            error = {'code': code, 'details': details}
            payload = {
                'status': 'error' if status_code >= 500 else 'fail',
                'error': error,
                'code': status_code,
                'message': message,
                'data': None,
            }
            return JsonResponse(payload, status=status_code)
        except Exception:
            return None
