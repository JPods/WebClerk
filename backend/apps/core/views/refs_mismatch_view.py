"""
refs_mismatch_view.py — the front end reports a FK ↔ refs.links mismatch it saw.

Written to the one Log, purpose refs_mismatch (apps/core/services/refs_mismatch.py). Read them
through the read channel: /wcapi/log/?purpose=refs_mismatch.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.services.refs_mismatch import log_refs_mismatch

logger = logging.getLogger(__name__)


class RefsMismatchView(APIView):
    """POST a mismatch report."""

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
        if not parent_model or not parent_id:
            return Response(
                {"status": "error", "message": "parent_model and parent_id are required"},
                status=400,
            )
        try:
            entry = log_refs_mismatch(
                parent_model=parent_model,
                parent_id=int(parent_id),
                related_model=data.get("related_model", "contact"),
                fk_field=data.get("fk_field", ""),
                fk_ids=[int(x) for x in data.get("fk_ids", []) if x is not None],
                refs_ids=[int(x) for x in data.get("refs_ids", []) if x is not None],
                caller=data.get("caller", ""),
                user=request.user,
                details=data.get("details") or None,
            )
        except Exception as e:
            logger.exception("[REFS_MISMATCH] Failed to log mismatch: %s", e)
            return Response({"status": "error", "message": str(e)}, status=500)

        if entry is None:
            return Response({"status": "ok", "message": "No mismatch detected"})
        found = entry.config["details"]
        logger.info("[REFS_MISMATCH] %s#%s ↔ %s: %s", parent_model, parent_id,
                    found["related_model"], entry.action)
        return Response({
            "status": "logged",
            "mismatch_type": entry.action,
            "only_in_fk": found["only_in_fk"],
            "only_in_refs": found["only_in_refs"],
        })
