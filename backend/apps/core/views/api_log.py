"""
API Log endpoint for receiving frontend log entries.
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection

from apps.core.models import APILog

logger = logging.getLogger(__name__)


class APILogView(APIView):
    """
    Endpoint to receive API log entries from React2025 frontend.
    
    POST /wcapi/log/api/
    {
        "source": "r25",
        "destination": "wc3",
        "method": "GET",
        "endpoint": "/wcapi/get/",
        "request_body": {...},
        "status_code": 200,
        "response_body": {...},
        "duration_ms": 150,
        "correlation_id": "r25-1234567890-abc123"
    }
    """
    
    def post(self, request, *args, **kwargs):
        data = request.data
        
        # Use savepoint to prevent log failures from affecting any transaction
        sid = connection.savepoint()
        try:
            APILog.log_request(
                source=data.get('source', 'r25'),
                destination=data.get('destination', 'wc3'),
                method=data.get('method', 'UNKNOWN'),
                endpoint=data.get('endpoint', ''),
                request_headers=data.get('request_headers', {}),
                request_body=data.get('request_body', {}),
                status_code=data.get('status_code'),
                response_headers=data.get('response_headers', {}),
                response_body=data.get('response_body', {}),
                error_message=data.get('error_message', ''),
                duration_ms=data.get('duration_ms'),
                correlation_id=data.get('correlation_id', ''),
                ip_address=self._get_client_ip(request),
                metadata=data.get('metadata', {}),
                request=request,
            )
            connection.savepoint_commit(sid)
            return Response({'status': 'logged'}, status=status.HTTP_201_CREATED)
        except Exception as e:
            connection.savepoint_rollback(sid)
            logger.warning("Failed to create API log: %s", str(e))
            # Don't fail the request - logging should be fire-and-forget
            return Response({'status': 'skipped', 'reason': str(e)}, status=status.HTTP_200_OK)
    
    @staticmethod
    def _get_client_ip(request) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
