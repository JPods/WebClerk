"""
refs_mismatch_view.py — API endpoint for logging FK ↔ refs.links mismatches.

The React front-end POSTs a comparison payload when it detects that FK-based
records and refs.links-based records don't agree.  This view persists the
mismatch to RefsMismatchLog for daily review.

Also provides a GET endpoint to retrieve recent mismatch history.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.models.refs_mismatch_log import RefsMismatchLog

logger = logging.getLogger(__name__)


class RefsMismatchView(APIView):
    """POST a mismatch report or GET recent mismatch history."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Log a FK ↔ refs mismatch detected by the front-end.

        Expected body:
        {
            "parent_model": "customer",
            "parent_id": 82,
            "related_model": "contact",
            "fk_field": "customer_id",
            "fk_ids": [1, 3, 5],
            "refs_ids": [3, 5],
            "caller": "CustomerDetail.useContacts"
        }
        """
        data = request.data or {}

        parent_model = data.get("parent_model")
        parent_id = data.get("parent_id")
        related_model = data.get("related_model", "contact")
        fk_field = data.get("fk_field", "")
        fk_ids = data.get("fk_ids", [])
        refs_ids = data.get("refs_ids", [])
        caller = data.get("caller", "")

        if not parent_model or not parent_id:
            return Response(
                {"status": "error", "message": "parent_model and parent_id are required"},
                status=400,
            )

        user_id = None
        if hasattr(request, "user") and request.user.is_authenticated:
            user_id = request.user.id

        try:
            entry = RefsMismatchLog.log_mismatch(
                parent_model=parent_model,
                parent_id=int(parent_id),
                related_model=related_model,
                fk_field=fk_field,
                fk_ids=[int(x) for x in fk_ids if x is not None],
                refs_ids=[int(x) for x in refs_ids if x is not None],
                caller=caller,
                user_id=user_id,
                details=data.get("details", {}),
            )

            if entry:
                logger.info(
                    "[REFS_MISMATCH] %s#%s ↔ %s: type=%s fk=%s refs=%s caller=%s",
                    parent_model, parent_id, related_model,
                    entry.mismatch_type, entry.fk_ids, entry.refs_ids, caller,
                )
                return Response({
                    "status": "logged",
                    "mismatch_type": entry.mismatch_type,
                    "only_in_fk": entry.only_in_fk,
                    "only_in_refs": entry.only_in_refs,
                })
            else:
                return Response({"status": "ok", "message": "No mismatch detected"})

        except Exception as e:
            logger.exception("[REFS_MISMATCH] Failed to log mismatch: %s", e)
            return Response(
                {"status": "error", "message": str(e)},
                status=500,
            )

    def get(self, request):
        """Return recent mismatch log entries for review.

        Query params:
            parent_model - Filter by parent model
            days - Number of days to look back (default: 7)
            limit - Max entries (default: 100)
        """
        from django.utils import timezone
        from datetime import timedelta

        parent_model = request.query_params.get("parent_model")
        days = int(request.query_params.get("days", 7))
        limit = int(request.query_params.get("limit", 100))

        since = timezone.now() - timedelta(days=days)
        qs = RefsMismatchLog.objects.filter(dt_created__gte=since)

        if parent_model:
            qs = qs.filter(parent_model=parent_model)

        entries = qs.order_by("-dt_created")[:limit]

        results = []
        for e in entries:
            results.append({
                "id": e.id,
                "dt_created": e.dt_created.isoformat() if e.dt_created else None,
                "parent_model": e.parent_model,
                "parent_id": e.parent_id,
                "related_model": e.related_model,
                "fk_field": e.fk_field,
                "mismatch_type": e.mismatch_type,
                "fk_ids": e.fk_ids,
                "refs_ids": e.refs_ids,
                "only_in_fk": e.only_in_fk,
                "only_in_refs": e.only_in_refs,
                "caller": e.caller,
                "user_id": e.user_id,
            })

        # Summary stats
        from django.db.models import Count
        summary = (
            RefsMismatchLog.objects
            .filter(dt_created__gte=since)
            .values("parent_model", "related_model", "mismatch_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        return Response({
            "status": "ok",
            "since": since.isoformat(),
            "total": len(results),
            "entries": results,
            "summary": list(summary),
        })
