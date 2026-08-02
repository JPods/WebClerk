"""
PDF report download endpoint.

GET /wcapi/report/?report=Invoice&model=invoice&id=62
GET /wcapi/report/?report=Statement&model=customer&id=15
GET /wcapi/report/?report=Pick+/+Pull+Request&model=order&id=100&format=html

Query params:
    report  — report name (matches reports.name)
    model   — model slug (e.g. invoice, order, customer)
    id      — optional record id for single-record reports
    format  — 'pdf' (default) or 'html'
    filters — optional JSON-encoded filter dict for list reports
"""
from __future__ import annotations

import json
import logging

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.api_responses import api_response

logger = logging.getLogger(__name__)


class ReportDownloadView(APIView):
    """Serve a rendered PDF (or HTML) for a named report."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        report_name = request.query_params.get("report", "").strip()
        model_name = request.query_params.get("model", "").strip()
        record_id = request.query_params.get("id")
        fmt = request.query_params.get("format", "pdf").strip().lower()
        filters_raw = request.query_params.get("filters")

        if not report_name:
            return api_response(
                success=False,
                status_code=400,
                message="'report' query parameter is required",
                error={"code": "missing_report"},
            )

        if not model_name:
            return api_response(
                success=False,
                status_code=400,
                message="'model' query parameter is required",
                error={"code": "missing_model"},
            )

        if record_id:
            try:
                record_id = int(record_id)
            except (ValueError, TypeError):
                return api_response(
                    success=False,
                    status_code=400,
                    message="'id' must be an integer",
                    error={"code": "invalid_id"},
                )

        filters = None
        if filters_raw:
            try:
                filters = json.loads(filters_raw)
            except json.JSONDecodeError:
                return api_response(
                    success=False,
                    status_code=400,
                    message="'filters' must be valid JSON",
                    error={"code": "invalid_filters"},
                )

        # Track usage — increment count on the Report record
        self._track_usage(report_name, model_name, request.user)

        try:
            from apps.core.services.report_renderer import render_report
            result = render_report(report_name, model_name, record_id, filters, fmt)
        except ValueError as e:
            return api_response(
                success=False,
                status_code=404,
                message=str(e),
                error={"code": "report_not_found"},
            )
        except Exception:
            logger.exception("Report rendering failed: %s / %s", report_name, model_name)
            return api_response(
                success=False,
                status_code=500,
                message="Report rendering failed",
                error={"code": "render_error"},
            )

        if fmt == "html":
            response = HttpResponse(result["html"], content_type="text/html")
            response["Content-Disposition"] = f'inline; filename="{result["filename"]}"'
            return response

        # PDF
        response = HttpResponse(result["pdf_bytes"], content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{result["filename"]}"'
        response["X-Report-Pages"] = str(result.get("pages", 0))
        return response

    @staticmethod
    def _track_usage(report_name: str, model_name: str, user) -> None:
        """Increment usage count on the Report record.

        Stored in metadata.flow:
            use_count:      total times this report has been generated
            last_used_utc:  ISO timestamp of last use
            used_by:        list of recent user IDs (last 20, deduplicated)
            first_used_utc: ISO timestamp of first use

        Alice uses this data to coach:
            - Reports never used → candidates for deactivation
            - Reports used heavily → protect from accidental deletion
            - Reports used by one person only → may be too specialized
            - Two reports with identical use patterns → may be duplicates
        """
        from datetime import datetime, timezone
        try:
            from apps.core.models import Report
            report = Report.objects.filter(
                name=report_name,
                model_name=model_name,
                is_active=True,
                is_deleted=False,
            ).first()
            if not report:
                return

            meta = report.metadata or {}
            flow = meta.get('flow', {}) or {}

            now = datetime.now(timezone.utc).isoformat()
            use_count = (flow.get('use_count') or 0) + 1
            first_used = flow.get('first_used_utc') or now

            # Track last 20 unique users
            used_by = flow.get('used_by') or []
            user_id = getattr(user, 'id', None)
            if user_id and user_id not in used_by:
                used_by.append(user_id)
            used_by = used_by[-20:]  # keep last 20

            flow['use_count'] = use_count
            flow['last_used_utc'] = now
            flow['first_used_utc'] = first_used
            flow['used_by'] = used_by

            meta['flow'] = flow
            report.metadata = meta
            report.save(update_fields=['metadata', 'dt_modified'])
        except Exception:
            # Never break report generation for a tracking failure
            pass
