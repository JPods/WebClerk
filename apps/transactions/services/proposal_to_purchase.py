from __future__ import annotations

from typing import Dict, List, Optional
from django.db import transaction

from apps.transactions.models import Proposal, ProposalLine, Purchase, PurchaseLine
from .transfer_utils import convert_quantity_from_source, select_lines, build_line_payload

class ProposalToPurchaseTransferError(Exception):
    pass

@transaction.atomic
def transfer_proposal_to_purchase(
    *,
    proposal: Proposal,
    line_ids: Optional[List[int]] = None,
    transfer_all: bool = False,
    purchase_status: str = "open",
    preserve_proposal: bool = True,
) -> Dict:
    qs = ProposalLine.objects.select_for_update().filter(parent=proposal)
    try:
        selected = select_lines(qs, line_ids, transfer_all)
    except ValueError as e:
        raise ProposalToPurchaseTransferError(str(e))

    po = Purchase.objects.create(
        status=purchase_status,
        refs={"source": {"proposal_id": proposal.id}},
    )

    line_mapping: Dict[int, int] = {}
    for pl in selected:
        qty = convert_quantity_from_source(pl.quantity or {}, "proposal")
        pol = PurchaseLine.objects.create(
            purchase=po,
            price=pl.price or {},
            cost=getattr(pl, "cost", None) or {},
            quantity=qty,
            refs={
                "source": {"proposal_line_id": pl.id},
                "xfer": build_line_payload(pl, "proposal"),
            },
        )
        line_mapping[pl.id] = pol.pk
        try:
            pl.status = "transferred"
            pl.save(update_fields=["status"])
        except Exception:
            pass

    if not preserve_proposal:
        try:
            proposal.status = "converted"
            proposal.save(update_fields=["status"])
        except Exception:
            pass

    return {
        "success": True,
        "purchase_order_id": po.id,
        "proposal_id": proposal.id,
        "lines_transferred": len(selected),
        "line_mapping": line_mapping,
        "order_status": purchase_status,
    }