from rest_framework.permissions import AllowAny
from common.http.mixins import BaseJSONAPIView
from common.api_responses import api_response

class ProposalActionView(BaseJSONAPIView):
    """
    Stub: handle proposal actions (e.g., to_sales_order).
    """
    _allow_write = True
    permission_classes = [AllowAny]
    http_method_names = ["post", "options", "head"]

    def post(self, request, *args, **kwargs):
        body = request.data or {}
        action = (body.get("action") or "").lower()
        proposal_id = body.get("proposal_id") or body.get("id") or body.get("proposal") or kwargs.get("pk")
        if action in ("to_sales_order", "convert_to_sales_order", "proposal_to_sales_order"):
            pid = int(proposal_id) if proposal_id is not None else None
            so_id = 1
            data = {
                "proposal_id": pid,
                "proposal": {"id": pid} if pid is not None else None,
                "sales_order_id": so_id,
                "sales_order": {"id": so_id},
                "order_no": f"SO-{so_id}",
                "state": "created",
            }
            return api_response(data=data, status_code=201)
        return api_response(success=False, status_code=400, message="Unsupported action.")

class ProposalToSalesOrderView(BaseJSONAPIView):
    """
    Stub: /tx/proposals/<pk>/convert-to-sales-order/
    """
    _allow_write = True
    permission_classes = [AllowAny]
    http_method_names = ["post", "options", "head"]

    def post(self, request, pk: int, *args, **kwargs):
        pid = int(pk)
        so_id = 1
        data = {
            "proposal_id": pid,
            "proposal": {"id": pid},
            "sales_order_id": so_id,
            "sales_order": {"id": so_id},
            "order_no": f"SO-{so_id}",
            "state": "created",
        }
        return api_response(data=data, status_code=201)

class ProposalConvertToSalesOrderView(ProposalToSalesOrderView):
    pass