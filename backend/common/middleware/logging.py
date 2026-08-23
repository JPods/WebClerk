"""Request/response logging middleware."""
import time
import uuid
import logging

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('request')
console_logger = logging.getLogger('console')


class RequestLogMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._req_start = time.time()
        request.request_id = uuid.uuid4().hex[:12]

        path = request.path
        method = request.method
        user = getattr(request, 'user', None)
        user_id = getattr(user, 'id', 'Anonymous') if user else 'Anonymous'
        console_logger.info(f"[WCAPI_DEBUG] REQUEST START - ID: {request.request_id} | {method} {path} | User: {user_id}")

    def process_response(self, request, response):
        try:
            dur_ms = int((time.time() - getattr(request, '_req_start', time.time())) * 1000)
            rid = getattr(request, 'request_id', '-')
            path = request.path
            user = getattr(request, 'user', None)
            uid = getattr(user, 'id', 0) if user and user.is_authenticated else 0
            status = response.status_code

            console_logger.info(f"[WCAPI_DEBUG] RESPONSE - ID: {rid} | {dur_ms}ms | Status: {status} | User: {uid} | {path}")
            logger.info(f"RID={rid} ms={dur_ms} status={status} user={uid} path={path}")
            response['X-Request-ID'] = rid
            response['X-Request-Duration-ms'] = str(dur_ms)
        except Exception as e:
            console_logger.error(f"[WCAPI_DEBUG] Error in middleware: {e}")
        return response
