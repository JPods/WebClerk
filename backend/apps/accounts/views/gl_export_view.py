"""
GL Export view — serves accounting program formatted downloads.

Called when user selects a GL Export report from the gl_journal report menu.

GET /wcapi/accounts/gl-export/?report=GL+Export+—+Generic+CSV&period=2026-08
GET /wcapi/accounts/gl-export/?report=GL+Export+—+QuickBooks+IIF&period=2026-08&division=10
"""
import logging

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.api_responses import api_response

logger = logging.getLogger(__name__)


class GlExportView(APIView):
    """Serve a GL journal export in a specific accounting format."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from apps.accounts.services.gl_export import gl_export, REPORT_NAME_MAP

        report_name = request.query_params.get('report', '').strip()
        period = request.query_params.get('period', '').strip()
        division = request.query_params.get('division', '').strip()

        if not report_name:
            return api_response(
                success=False, status_code=400,
                message="'report' query parameter is required",
                error={'code': 'missing_report'},
            )

        if not period:
            return api_response(
                success=False, status_code=400,
                message="'period' query parameter is required (YYYY-MM)",
                error={'code': 'missing_period'},
            )

        # Validate period format
        try:
            parts = period.split('-')
            if len(parts) != 2:
                raise ValueError
            year, month = int(parts[0]), int(parts[1])
            if not (2000 <= year <= 2099 and 1 <= month <= 12):
                raise ValueError
        except (ValueError, IndexError):
            return api_response(
                success=False, status_code=400,
                message="'period' must be YYYY-MM format (e.g. 2026-08)",
                error={'code': 'invalid_period'},
            )

        adapter = REPORT_NAME_MAP.get(report_name)
        if not adapter:
            return api_response(
                success=False, status_code=404,
                message=f"Unknown GL export format: {report_name}",
                error={'code': 'unknown_format', 'available': list(REPORT_NAME_MAP.keys())},
            )

        try:
            content, filename, content_type = gl_export(period, adapter, division)
        except Exception:
            logger.exception("GL export failed: %s / %s", report_name, period)
            return api_response(
                success=False, status_code=500,
                message="GL export failed",
                error={'code': 'export_error'},
            )

        # Track usage on the Report record
        self._track_usage(report_name, request.user)

        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @staticmethod
    def _track_usage(report_name: str, user) -> None:
        """Increment usage count on the Report record."""
        from datetime import datetime, timezone
        try:
            from apps.core.models import Report
            report = Report.objects.filter(
                name=report_name, model_name='gl_journal',
                is_active=True, is_deleted=False,
            ).first()
            if not report:
                return

            meta = report.metadata or {}
            flow = meta.get('flow', {}) or {}

            now = datetime.now(timezone.utc).isoformat()
            flow['use_count'] = (flow.get('use_count') or 0) + 1
            flow['last_used_utc'] = now
            flow.setdefault('first_used_utc', now)

            used_by = flow.get('used_by') or []
            user_id = getattr(user, 'id', None)
            if user_id and user_id not in used_by:
                used_by.append(user_id)
            flow['used_by'] = used_by[-20:]

            meta['flow'] = flow
            report.metadata = meta
            report.save(update_fields=['metadata', 'dt_modified'])
        except Exception:
            pass
