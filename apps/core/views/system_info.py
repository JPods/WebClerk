"""
System Info View - Returns data set identification and system metadata.

This endpoint helps identify which environment/database the frontend
and backend are communicating with.

Includes pending queue health: flags when unprocessed pending records
are older than 3 minutes (sign of stuck/deadlocked processes).
"""
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from decouple import config
import platform
import django

# 3 minutes in milliseconds — threshold for stale pending records
PENDING_STALE_MS = 3 * 60 * 1000


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

        # Pending queue health check
        pending_health = self._check_pending_health()

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
            'pending': pending_health,
            'message': f"Connected to {data_set_name} ({data_set_id})"
        })

    @staticmethod
    def _check_pending_health():
        """Check for stale unprocessed pending records.

        Returns a dict with count, oldest_age_seconds, and a stale flag.
        Stale = count > 0 AND oldest record > 3 minutes old.
        """
        try:
            from apps.core.models.pending import Pending
            now_ms = int(timezone.now().timestamp() * 1000)
            cutoff_ms = now_ms - PENDING_STALE_MS

            unprocessed = Pending.objects.filter(dt_processed=0)
            count = unprocessed.count()

            if count == 0:
                return {'count': 0, 'stale': False, 'oldest_age_seconds': 0}

            oldest_dt = unprocessed.order_by('dt_created').values_list('dt_created', flat=True).first()
            oldest_age_seconds = round((now_ms - oldest_dt) / 1000) if oldest_dt else 0
            stale = oldest_dt < cutoff_ms if oldest_dt else False

            return {
                'count': count,
                'stale': stale,
                'oldest_age_seconds': oldest_age_seconds,
            }
        except Exception:
            return {'count': -1, 'stale': False, 'oldest_age_seconds': 0}
