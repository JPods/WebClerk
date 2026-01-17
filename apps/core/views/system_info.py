"""
System Info View - Returns data set identification and system metadata.

This endpoint helps identify which environment/database the frontend 
and backend are communicating with.
"""
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from decouple import config
import platform
import django


class SystemInfoView(APIView):
    """
    Public endpoint that returns system identification info.
    
    Used to verify frontend and backend are pointing to the same data set.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Get data set identification from environment
        data_set_id = config('DATA_SET_ID', default='UNKNOWN')
        data_set_name = config('DATA_SET_NAME', default='Unknown Environment')
        
        # Get database info (sanitized - no credentials)
        db_host = config('DATABASE_HOST', default='unknown')
        db_name = config('DATABASE_NAME', default='unknown')
        
        # Mask the host for security (show only last segment)
        if db_host and db_host not in ['localhost', '127.0.0.1', 'unknown']:
            # Show partial IP for identification without full exposure
            parts = db_host.split('.')
            if len(parts) == 4:
                db_host_masked = f"***.***.***.{parts[-1]}"
            else:
                db_host_masked = db_host[:3] + '***'
        else:
            db_host_masked = db_host
        
        return Response({
            'data_set': {
                'id': data_set_id,
                'name': data_set_name,
            },
            'database': {
                'host': db_host_masked,
                'name': db_name,
            },
            'server': {
                'debug': settings.DEBUG,
                'django_version': django.VERSION[:3],
                'python_version': platform.python_version(),
            },
            'message': f"Connected to {data_set_name} ({data_set_id})"
        })
