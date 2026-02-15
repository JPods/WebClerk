from typing import List
from rest_framework.permissions import IsAuthenticated
from common.api_responses import api_response

# Prefer project BaseJSONAPIView; fallback to DRF APIView
try:
    from apps.core.views import BaseJSONAPIView
except ImportError:
    from rest_framework.views import APIView as BaseJSONAPIView

# Try importing line models; skip any that aren't available
try:
    from apps.transactions.models.proposal_line import ProposalLine
except Exception:
    ProposalLine = None  # type: ignore

try:
    from apps.transactions.models.order_line import OrderLine
except Exception:
    OrderLine = None  # type: ignore

try:
    from apps.transactions.models.invoice_line import InvoiceLine
except Exception:
    InvoiceLine = None  # type: ignore

try:
    from apps.transactions.models.purchase_line import PurchaseLine
except Exception:
    PurchaseLine = None  # type: ignore


class LinkageCommentsView(BaseJSONAPIView):
    """
    GET /tx/linkages/<linkage_id>/comments/
    Aggregate 'public' comments from any line whose refs.links.linkage contains linkage_id.
    """
    _allow_write = False
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "options", "head"]

    def get(self, request, linkage_id: int, *args, **kwargs):
        public_comments: List[str] = []
        items: List[dict] = []

        def collect_from_qs(qs, model_name: str):
            nonlocal public_comments, items
            if not qs:
                return
            for line in qs:
                refs = getattr(line, "refs", None) or {}
                try:
                    linkage = (refs.get("links") or {}).get("linkage") or []
                except Exception:
                    linkage = []
                if isinstance(linkage, list) and linkage_id in linkage:
                    comments = getattr(line, "comments", None) or {}
                    pub = comments.get("public") if isinstance(comments, dict) else None
                    if isinstance(pub, str) and pub:
                        public_comments.append(pub)
                        items.append({
                            "comments": {"public": pub},
                            "source": {"model": model_name, "id": line.id},
                        })

        if ProposalLine is not None:
            collect_from_qs(ProposalLine.objects.filter(refs__isnull=False), "proposal_line")
        if OrderLine is not None:
            collect_from_qs(OrderLine.objects.filter(refs__isnull=False), "order_line")
        if InvoiceLine is not None:
            collect_from_qs(InvoiceLine.objects.filter(refs__isnull=False), "invoice_line")
        if PurchaseLine is not None:
            collect_from_qs(PurchaseLine.objects.filter(refs__isnull=False), "purchase_line")

        data = {
            "linkage_id": linkage_id,
            "items": items,
            "comments": {
                "public": public_comments,              # keep flat alias
                "general": {"public": public_comments}, # test expects this shape
            },
            "count": len(items),
        }
        return api_response(data=data, status_code=200)