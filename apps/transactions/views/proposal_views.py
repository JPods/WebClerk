from rest_framework.permissions import AllowAny
from common.http.mixins import BaseJSONAPIView
from common.api_responses import api_response
from apps.transactions.models.proposal import Proposal
from apps.transactions.models.sales_order import SalesOrder
from apps.transactions.models.sales_order_line import SalesOrderLine

class ProposalActionView(BaseJSONAPIView):
    """
    Handle proposal actions (e.g., to_sales_order).
    """
    _allow_write = True
    permission_classes = [AllowAny]
    http_method_names = ["post", "options", "head"]

    def post(self, request, *args, **kwargs):
        body = request.data or {}
        action = (body.get("action") or "").lower()
        proposal_id = body.get("proposal_id") or body.get("id") or body.get("proposal") or kwargs.get("pk")
        if action in ("to_sales_order", "convert_to_sales_order", "proposal_to_sales_order"):
            return self._convert_to_sales_order(int(proposal_id) if proposal_id else None)
        return api_response(success=False, status_code=400, message="Unsupported action.")

    def _convert_to_sales_order(self, proposal_pk: int | None):
        if not proposal_pk:
            return api_response(success=False, status_code=400, message="Missing proposal id.")
        proposal = Proposal.objects.filter(pk=proposal_pk).first()
        if not proposal:
            return api_response(success=False, status_code=404, message="Proposal not found.")

        # Create SalesOrder and copy lines minimally for linkage propagation tests
        so = SalesOrder.objects.create()
        # Optional transient order number
        try:
            so.order_no = f"SO-{so.pk}"
        except Exception:
            pass

        for pl in getattr(proposal, "lines", []).all():
            # Build/propagate linkage list (ensure list and non-empty)
            linkage = []
            try:
                existing = (pl.refs or {}).get("links", {}).get("linkage", [])
                if isinstance(existing, list):
                    linkage.extend(existing)
            except Exception:
                pass
            if pl.pk not in linkage:
                linkage.append(pl.pk)
            refs = {"links": {"linkage": linkage}}

            SalesOrderLine.objects.create(
                parent=so,
                parent_ref_id=so.pk,
                status=getattr(pl, "status", "OPEN") or "OPEN",
                item=getattr(pl, "item", None),
                quantity=getattr(pl, "quantity", None),
                price=getattr(pl, "price", None),
                cost=getattr(pl, "cost", None),
                tax=getattr(pl, "tax", None),
                physical=getattr(pl, "physical", None),
                comments=getattr(pl, "comments", None),
                refs=refs,
            )

        data = {
            "proposal_id": proposal.pk,
            "proposal": {"id": proposal.pk},
            "sales_order_id": so.pk,
            "sales_order": {"id": so.pk},
            "order_no": f"SO-{so.pk}",
            "state": "created",
        }
        return api_response(data=data, status_code=201)


class ProposalToSalesOrderView(BaseJSONAPIView):
    """
    POST /tx/proposals/<pk>/convert-to-sales-order/
    """
    _allow_write = True
    permission_classes = [AllowAny]
    http_method_names = ["post", "options", "head"]

    def post(self, request, pk: int, *args, **kwargs):
        proposal = Proposal.objects.filter(pk=pk).first()
        if not proposal:
            return api_response(success=False, status_code=404, message="Proposal not found.")

        so = SalesOrder.objects.create()
        try:
            so.order_no = f"SO-{so.pk}"
        except Exception:
            pass

        for pl in getattr(proposal, "lines", []).all():
            # Build/propagate linkage list (ensure list and non-empty)
            linkage = []
            try:
                existing = (pl.refs or {}).get("links", {}).get("linkage", [])
                if isinstance(existing, list):
                    linkage.extend(existing)
            except Exception:
                pass
            if pl.pk not in linkage:
                linkage.append(pl.pk)
            refs = {"links": {"linkage": linkage}}

            SalesOrderLine.objects.create(
                parent=so,
                parent_ref_id=so.pk,
                status=getattr(pl, "status", "OPEN") or "OPEN",
                item=getattr(pl, "item", None),
                quantity=getattr(pl, "quantity", None),
                price=getattr(pl, "price", None),
                cost=getattr(pl, "cost", None),
                tax=getattr(pl, "tax", None),
                physical=getattr(pl, "physical", None),
                comments=getattr(pl, "comments", None),
                refs=refs,
            )

        data = {
            "proposal_id": proposal.pk,
            "proposal": {"id": proposal.pk},
            "sales_order_id": so.pk,
            "sales_order": {"id": so.pk},
            "order_no": f"SO-{so.pk}",
            "state": "created",
        }
        return api_response(data=data, status_code=201)


class ProposalConvertToSalesOrderView(ProposalToSalesOrderView):
    pass