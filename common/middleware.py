import time, uuid, logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('request')

class RequestLogMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._req_start = time.time()
        request.request_id = uuid.uuid4().hex[:12]
    def process_response(self, request, response):
        try:
            dur_ms = int((time.time() - getattr(request, '_req_start', time.time())) * 1000)
            rid = getattr(request, 'request_id', '-')
            path = request.path
            user = getattr(request, 'user', None)
            uid = getattr(user, 'id', 0) if user and user.is_authenticated else 0
            logger.info(f"RID={rid} ms={dur_ms} status={response.status_code} user={uid} path={path}")
            response['X-Request-ID'] = rid
            response['X-Request-Duration-ms'] = str(dur_ms)
        except Exception:
            pass
        return response
