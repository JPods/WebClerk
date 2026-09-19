from __future__ import annotations

from typing import Dict, List, Optional
from django.db import transaction

from apps.transactions.models import Purchase, PurchaseLine, Quote, QuoteLine
from .convert_utils import convert_quantity_from_source, select_lines, build_line_payload

class PurchaseToQuoteTransferError(Exception):
    pass

@transaction.atomic
def transfer_purchase_to_quote(
    *,
    purchase: Purchase,
    line_ids: Optional[List[int]] = None,
    transfer_all: bool = False,
    quote_status: str = "draft",
    preserve_purchase: bool = True,
) -> Dict:
    qs = PurchaseLine.objects.select_for_update().filter(purchase=purchase)
    try:
        selected = select_lines(qs, line_ids, transfer_all)
    except ValueError as e:
        raise PurchaseToQuoteTransferError(str(e))

    prop = Quote.objects.create(
        status=quote_status,
        refs={"source": {"purchase_id": purchase.id}},
    )

    line_mapping: Dict[int, int] = {}
    for pl in selected:
        qty = convert_quantity_from_source(getattr(pl, "quantity", None) or {}, "purchase")
        tl = QuoteLine.objects.create(
            quote=prop,
            price=getattr(pl, "price", None) or {},
            cost=getattr(pl, "cost", None) or {},
            quantity=qty,
            refs={
                "source": {"purchase_line_id": pl.pk},
                "xfer": build_line_payload(pl, "purchase"),
            },
        )
        line_mapping[pl.pk] = tl.id
        # No status field on PurchaseLine; transfer is tracked via refs and mapping.
        # If a status is needed, add a model field and update here accordingly.
        
    if not preserve_purchase:
        try:
            purchase.status = "converted"
            purchase.save(update_fields=["status"])
        except Exception:
            pass

    return {
        "success": True,
        "quote_id": prop.id,
        "purchase_id": purchase.id,
        "lines_transferred": len(selected),
        "line_mapping": line_mapping,
        "quote_status": quote_status,
    }