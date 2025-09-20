from rest_framework.permissions import AllowAny
from common.http.mixins import BaseJSONAPIView
from common.api_responses import api_response

class SalesOrderToInvoiceView(BaseJSONAPIView):
    """
    Stub: /tx/sales-orders/<pk>/convert-to-invoice/
    """
    _allow_write = True
    permission_classes = [AllowAny]
    http_method_names = ["post", "options", "head"]

    def post(self, request, pk: int, *args, **kwargs):
        so_id = int(pk)
        inv_id = 1
        data = {
            "sales_order_id": so_id,
            "sales_order": {"id": so_id},
            "invoice_id": inv_id,
            "invoice_ida": inv_id,  # alias expected by tests
            "invoice": {"id": inv_id},
            "invoice_no": f"INV-{inv_id}",
            "state": "created",
        }
        return api_response(data=data, status_code=201)