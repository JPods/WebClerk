from __future__ import annotations

from typing import Dict, List, Optional
from django.db import transaction
from collections import defaultdict

from apps.transactions.models import Order, OrderLine, Purchase, PurchaseLine
from .convert_utils import convert_quantity_from_source, select_lines, build_line_payload

class OrderToPurchaseTransferError(Exception):
    pass

@transaction.atomic
def transfer_order_to_purchase(
    *,
    order: Order,
    line_ids: Optional[List[int]] = None,
    transfer_all: bool = False,
    purchase_status: str = "planned",
    preserve_order: bool = True,
    group_by_vendor: bool = True,
) -> Dict:
    """
    Transfer order lines to purchase orders, optionally grouping by vendor.
    Creates separate POs for each vendor if group_by_vendor=True.
    """
    qs = OrderLine.objects.select_for_update().filter(order=order)
    try:
        selected = select_lines(qs, line_ids, transfer_all)
    except ValueError as e:
        raise OrderToPurchaseTransferError(str(e))

    # Group lines by vendor if requested
    vendor_groups = defaultdict(list)
    if group_by_vendor:
        for sl in selected:
            vendor_id = (
                (sl.item or {}).get('vendor_id')
                or getattr(sl, 'vendor_id', None)
                or order.vendor_id
            )
            vendor_groups[vendor_id].append(sl)
    else:
        # All lines to one PO
        vendor_groups[order.vendor_id or 0] = selected

    purchases = []
    line_mapping: Dict[int, int] = {}

    for vendor_id, lines in vendor_groups.items():
        # Create PO for this vendor
        po = Purchase.objects.create(
            status=purchase_status,
            vendor_id=vendor_id,
            customer_id=order.customer_id,
            refs={"source": {"order_id": order.id}},
            metadata={"expected_delivery": None},  # Can be set later
        )

        for sl in lines:
            qty = convert_quantity_from_source(sl.quantity or {}, "order")
            pol = PurchaseLine.objects.create(
                purchase=po,
                cost=getattr(sl, "cost", None) or {},
                quantity=qty,
                item=sl.item or {},
                refs={
                    "source": {"order_line_id": sl.id},
                    "xfer": build_line_payload(sl, "order"),
                },
                metadata={"expected_delivery": None},  # Per line if needed
            )
            line_mapping[sl.id] = pol.pk
            try:
                sl.status = "transferred"
                sl.save(update_fields=["status"])
            except Exception:
                pass

        purchases.append(po)

    if not preserve_order:
        try:
            order.status = "converted"
            order.save(update_fields=["status"])
        except Exception:
            pass

    # Update totals for created POs
    for po in purchases:
        po.update_sell_cost_totals(persist=True)

    return {
        "success": True,
        "purchase_ids": [po.id for po in purchases],
        "order_id": order.id,
        "lines_transferred": len(selected),
        "line_mapping": line_mapping,
        "order_status": purchase_status,
        "vendor_groups": len(vendor_groups),
    }