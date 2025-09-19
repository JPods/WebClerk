from __future__ import annotations

from typing import Dict, List, Optional
from django.db import transaction

from apps.transactions.models import SalesOrder, SalesOrderLine, PurchaseOrder, PurchaseOrderLine
from .transfer_utils import convert_quantity_from_source, select_lines, build_line_payload

class OrderToPurchaseTransferError(Exception):
    pass

@transaction.atomic
def transfer_order_to_purchase(
    *,
    order: SalesOrder,
    line_ids: Optional[List[int]] = None,
    transfer_all: bool = False,
    purchase_status: str = "open",
    preserve_order: bool = True,
) -> Dict:
    qs = SalesOrderLine.objects.select_for_update().filter(parent=order)
    try:
        selected = select_lines(qs, line_ids, transfer_all)
    except ValueError as e:
        raise OrderToPurchaseTransferError(str(e))

    po = PurchaseOrder.objects.create(
        status=purchase_status,
        refs={"source": {"sales_order_id": order.id}},
    )

    line_mapping: Dict[int, int] = {}
    for sl in selected:
        qty = convert_quantity_from_source(sl.quantity or {}, "sales_order")
        pol = PurchaseOrderLine.objects.create(
            parent=po,
            price=sl.price or {},
            cost=getattr(sl, "cost", None) or {},
            quantity=qty,
            refs={
                "source": {"sales_order_line_id": sl.id},
                "xfer": build_line_payload(sl, "sales_order"),
            },
        )
        line_mapping[sl.id] = pol.pk
        try:
            sl.status = "transferred"
            sl.save(update_fields=["status"])
        except Exception:
            pass

    if not preserve_order:
        try:
            order.status = "converted"
            order.save(update_fields=["status"])
        except Exception:
            pass

    return {
        "success": True,
        "purchase_order_id": po.id,
        "sales_order_id": order.id,
        "lines_transferred": len(selected),
        "line_mapping": line_mapping,
        "order_status": purchase_status,
    }