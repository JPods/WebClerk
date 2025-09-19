from __future__ import annotations

from typing import Dict, List, Optional
from django.db import transaction

from apps.transactions.models import PurchaseOrder, PurchaseOrderLine, SalesOrder, SalesOrderLine
from .transfer_utils import convert_quantity_from_source, select_lines, build_line_payload

class PurchaseToOrderTransferError(Exception):
    pass

@transaction.atomic
def transfer_purchase_to_order(
    *,
    purchase: PurchaseOrder,
    line_ids: Optional[List[int]] = None,
    transfer_all: bool = False,
    order_status: str = "confirmed",
    preserve_purchase: bool = True,
) -> Dict:
    qs = PurchaseOrderLine.objects.select_for_update().filter(parent=purchase)
    try:
        selected = select_lines(qs, line_ids, transfer_all)
    except ValueError as e:
        raise PurchaseToOrderTransferError(str(e))

    so = SalesOrder.objects.create(
        status=order_status,
        refs={"source": {"purchase_order_id": purchase.id}},
    )

    line_mapping: Dict[int, int] = {}
    for pl in selected:
        qty = convert_quantity_from_source(getattr(pl, "quantity", None) or {}, "purchase_order")
        sl = SalesOrderLine.objects.create(
            parent=so,
            price=getattr(pl, "price", None) or {},
            cost=getattr(pl, "cost", None) or {},
            quantity=qty,
            refs={
                "source": {"purchase_order_line_id": pl.pk},
                "xfer": build_line_payload(pl, "purchase_order"),
            },
        )
        line_mapping[pl.pk] = sl.id
        # Update status only if the model actually has the field
        if any(getattr(f, "name", None) == "status" for f in pl._meta.get_fields()):
            setattr(pl, "status", "transferred")
            pl.save(update_fields=["status"])

    if not preserve_purchase:
        # Update status only if the model actually has the field
        if any(getattr(f, "name", None) == "status" for f in purchase._meta.get_fields()):
            setattr(purchase, "status", "converted")
            purchase.save(update_fields=["status"])

    return {
        "sales_order_id": so.id,
        "purchase_order_id": purchase.id,
        "lines_transferred": len(selected),
        "line_mapping": line_mapping,
        "order_status": order_status,
    }