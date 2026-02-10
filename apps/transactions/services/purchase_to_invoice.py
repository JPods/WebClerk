from __future__ import annotations

from typing import Dict, List, Optional
from django.db import transaction

from apps.transactions.models import Purchase, PurchaseLine, Invoice, InvoiceLine
from .transfer_utils import convert_quantity_from_source, select_lines, build_line_payload

class PurchaseToInvoiceTransferError(Exception):
    pass

@transaction.atomic
def transfer_purchase_to_invoice(
    *,
    purchase: Purchase,
    line_ids: Optional[List[int]] = None,
    transfer_all: bool = False,
    invoice_status: str = "draft",
    preserve_purchase: bool = True,
) -> Dict:
    qs = PurchaseLine.objects.select_for_update().filter(purchase=purchase)
    try:
        selected = select_lines(qs, line_ids, transfer_all)
    except ValueError as e:
        raise PurchaseToInvoiceTransferError(str(e))

    inv = Invoice.objects.create(
        status=invoice_status,
        refs={"source": {"purchase_order_id": purchase.id}},
    )

    line_mapping: Dict[int, int] = {}
    for pl in selected:
        qty = convert_quantity_from_source(getattr(pl, "quantity", {}) or {}, "purchase_order")
        il = InvoiceLine.objects.create(
            invoice=inv,
            price=getattr(pl, "price", None) or {},
            cost=getattr(pl, "cost", None) or {},
            quantity=qty,
            refs={
                "source": {"purchase_order_line_id": pl.pk},
                "xfer": build_line_payload(pl, "purchase_order"),
            },
        )
        line_mapping[pl.pk] = il.pk
        try:
            PurchaseLine.objects.filter(pk=pl.pk).update(status="transferred")
        except Exception:
            pass

    if not preserve_purchase:
        try:
            Purchase.objects.filter(pk=purchase.pk).update(status="converted")
        except Exception:
            pass
    return {
        "success": True,
        "invoice_id": inv.id,
        "purchase_order_id": purchase.id,
        "lines_transferred": len(selected),
        "line_mapping": line_mapping,
        "invoice_status": invoice_status,
    }