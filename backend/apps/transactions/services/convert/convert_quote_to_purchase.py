from __future__ import annotations

from typing import Dict, List, Optional
from django.db import transaction

from apps.transactions.models import Quote, QuoteLine, Purchase, PurchaseLine
from .convert_utils import convert_quantity_from_source, select_lines, build_line_payload

class QuoteToPurchaseTransferError(Exception):
    pass

@transaction.atomic
def transfer_quote_to_purchase(
    *,
    quote: Quote,
    line_ids: Optional[List[int]] = None,
    transfer_all: bool = False,
    purchase_status: str = "open",
    preserve_quote: bool = True,
) -> Dict:
    qs = QuoteLine.objects.select_for_update().filter(quote=quote)
    try:
        selected = select_lines(qs, line_ids, transfer_all)
    except ValueError as e:
        raise QuoteToPurchaseTransferError(str(e))

    po = Purchase.objects.create(
        status=purchase_status,
        refs={"source": {"quote_id": quote.id}},
    )

    line_mapping: Dict[int, int] = {}
    for pl in selected:
        qty = convert_quantity_from_source(pl.quantity or {}, "quote")
        pol = PurchaseLine.objects.create(
            purchase=po,
            price=pl.price or {},
            cost=getattr(pl, "cost", None) or {},
            quantity=qty,
            refs={
                "source": {"quote_line_id": pl.id},
                "xfer": build_line_payload(pl, "quote"),
            },
        )
        line_mapping[pl.id] = pol.pk
        # Not parent-child: the source line's status is untouched (readmes/transactions/line-quantity.md).

    if not preserve_quote:
        try:
            quote.status = "converted"
            quote.save(update_fields=["status"])
        except Exception:
            pass

    return {
        "success": True,
        "purchase_id": po.id,
        "quote_id": quote.id,
        "lines_transferred": len(selected),
        "line_mapping": line_mapping,
        "order_status": purchase_status,
    }