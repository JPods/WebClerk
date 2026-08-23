from __future__ import annotations

from typing import Dict, List, Optional
from django.db import transaction

from apps.transactions.models import Invoice, InvoiceLine, Purchase, PurchaseLine
from .transfer_utils import convert_quantity_from_source, select_lines, build_line_payload

class InvoiceToPurchaseTransferError(Exception):
    pass

@transaction.atomic
def transfer_invoice_to_purchase(
    *,
    invoice: Invoice,
    line_ids: Optional[List[int]] = None,
    transfer_all: bool = False,
    purchase_status: str = "open",
    preserve_invoice: bool = True,
) -> Dict:
    qs = InvoiceLine.objects.select_for_update().filter(invoice=invoice)
    try:
        selected = select_lines(qs, line_ids, transfer_all)
    except ValueError as e:
        raise InvoiceToPurchaseTransferError(str(e))

    po = Purchase.objects.create(
        status=purchase_status,
        refs={"source": {"invoice_id": invoice.pk}},
    )

    line_mapping: Dict[int, int] = {}
    for il in selected:
        qty = convert_quantity_from_source(il.quantity or {}, "invoice")
        pol = PurchaseLine.objects.create(
            purchase=po,
            price=il.price or {},
            cost=getattr(il, "cost", None) or {},
            quantity=qty,
            refs={
                "source": {"invoice_line_id": il.pk},
                "xfer": build_line_payload(il, "invoice"),
            },
        )
        line_mapping[il.pk] = pol.pk
        try:
            il.status = "transferred"
            il.save(update_fields=["status"])
        except Exception:
            pass

    if not preserve_invoice:
        try:
            invoice.status = "converted"
            invoice.save(update_fields=["status"])
        except Exception:
            pass

    return {
        "success": True,
        "purchase_id": po.pk,
        "invoice_id": invoice.pk,
        "lines_transferred": len(selected),
        "line_mapping": line_mapping,
        "order_status": purchase_status,
    }