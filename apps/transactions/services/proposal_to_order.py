from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Tuple

from django.db import transaction

from apps.transactions.models import (
    Proposal,
    ProposalLine,
    Order,
    OrderLine,
)
from .transfer_utils import build_line_payload


class ProposalToOrderTransferError(Exception):
    """Business-rule violation during proposal-to-order transfer."""


def _sum_price_extended(lines: Iterable[ProposalLine]) -> float:
    total = Decimal(0)
    for ln in lines:
        p = (ln.price or {})
        try:
            total += Decimal(str(p.get("extended", 0) or 0))
        except Exception:
            # Be forgiving if price is malformed
            total += Decimal(0)
    return float(total)


def validate_proposal_for_transfer(
    proposal: Optional[Proposal],
    line_ids: Optional[List[int]] = None,
) -> Dict:
    """
    Returns:
      {
        'can_transfer': bool,
        'errors': [str],
        'warnings': [str],
        'line_count': int,
        'total_amount': float,
      }
    """
    errors: List[str] = []
    warnings: List[str] = []

    if proposal is None:
        return {
            "can_transfer": False,
            "errors": ["Proposal not found"],
            "warnings": [],
            "line_count": 0,
            "total_amount": 0.0,
        }

    qs = ProposalLine.objects.filter(parent=proposal)

    if line_ids is not None:
        existing = set(qs.filter(id__in=line_ids).values_list("id", flat=True))
        missing = [i for i in line_ids if i not in existing]
        if missing:
            errors.append(f"Line IDs not found: {missing}")

    line_count = qs.count()
    if line_count == 0:
        errors.append("No lines to transfer")

    # Warnings based on statuses
    if getattr(proposal, "status", "") == "converted":
        warnings.append("Proposal status is converted")

    transferred_cnt = qs.filter(status="transferred").count()
    if transferred_cnt:
        warnings.append("Some lines already transferred" if transferred_cnt > 1 else "Line already transferred")

    total_amount = _sum_price_extended(qs)

    can_transfer = len(errors) == 0
    return {
        "can_transfer": can_transfer,
        "errors": errors,
        "warnings": warnings,
        "line_count": line_count,
        "total_amount": total_amount,
    }


def _convert_quantity_from_proposal(proposal_qty: Optional[Dict]) -> Dict:
    """
    Convert proposal line quantity structure to order line quantity structure.

    - Use 'placed' if present, else 'ordered', else 'remaining', else 0 as base.
    - Preserve precision/is_fixed when present.
    - Add converted_from_proposal with original keys and values.
    """
    q = proposal_qty or {}
    has_placed = "placed" in q
    base = q.get("placed")
    if base is None:
        base = q.get("ordered", q.get("remaining", 0))

    converted_from_proposal = {
        "is_blanket": q.get("is_blanket", False),
        "increment": q.get("increment", 0),
        "original_remaining": q.get("remaining", 0),
    }
    # Record original base key for compatibility with tests
    if has_placed:
        converted_from_proposal["original_placed"] = q.get("placed", 0)
    else:
        converted_from_proposal["original_ordered"] = q.get("ordered", 0)

    order_qty = {
        "invoiced": 0,
        "remaining": base or 0,
    }
    if "precision" in q:
        order_qty["precision"] = q["precision"]
    if "is_fixed" in q:
        order_qty["is_fixed"] = q["is_fixed"]

    order_qty["converted_from_proposal"] = converted_from_proposal
    return order_qty


@transaction.atomic
def transfer_proposal_to_order(
    *,
    proposal: Proposal,
    line_ids: Optional[List[int]] = None,
    transfer_all: bool = False,
    order_status: str = "confirmed",
    preserve_proposal: bool = True,
) -> Dict:
    """
    Transfer proposal lines to a new order.

    Returns:
      {
        'success': True,
        'order_id': int,
        'proposal_id': int,
        'lines_transferred': int,
        'line_mapping': {proposal_line_id: order_line_id, ...},
        'proposal_preserved': bool,
        'order_status': str,
      }
    """
    if not transfer_all and not line_ids:
        raise ProposalToOrderTransferError("Must specify line_ids when transfer_all is False")

    all_lines_qs = ProposalLine.objects.select_for_update().filter(parent=proposal)
    if transfer_all:
        selected_lines = list(all_lines_qs)
        if not selected_lines:
            raise ProposalToOrderTransferError("No lines to transfer")
    else:
        selected_lines = list(all_lines_qs.filter(id__in=line_ids))
        if not selected_lines:
            raise ProposalToOrderTransferError("Line IDs not found")

    order_kwargs = {
        "status": order_status,
        "refs": {"source": {"proposal_id": proposal.id}},
    }
    # Copy party_id only if Order supports it and proposal provides it
    proposal_party_id = getattr(proposal, "party_id", None)
    if proposal_party_id is not None and hasattr(Order(), "party_id"):
        order_kwargs["party_id"] = proposal_party_id

    order = Order.objects.create(**order_kwargs)

    # If party_id wasn't accepted at create but exists, set after
    if hasattr(order, "party_id") and proposal_party_id is not None and "party_id" not in order_kwargs:
        try:
            setattr(order, "party_id", proposal_party_id)
            order.save(update_fields=["party_id"])
        except Exception:
            # Ignore if field doesn't exist or is read-only
            pass

    # Create order lines and map from proposal lines
    line_mapping: Dict[int, int] = {}
    for pl in selected_lines:
        qty = _convert_quantity_from_proposal(getattr(pl, "quantity", None))
        ol = OrderLine.objects.create(
            parent=order,
            price=pl.price or {},
            cost=getattr(pl, "cost", None) or {},
            quantity=qty,
            refs={
                "source": {"proposal_line_id": pl.id},
                "xfer": build_line_payload(pl, "proposal"),  # common payload array
            },
        )
        line_mapping[pl.id] = ol.id

        # Mark proposal line as transferred
        try:
            pl.status = "transferred"
            pl.save(update_fields=["status"])
        except Exception:
            # If status field does not exist, ignore
            pass

    # Update proposal if not preserving
    if not preserve_proposal:
        try:
            proposal.status = "converted"
            proposal.save(update_fields=["status"])
        except Exception:
            pass

    return {
        "success": True,
        "order_id": order.id,
        "proposal_id": proposal.id,
        "lines_transferred": len(selected_lines),
        "line_mapping": line_mapping,
        "proposal_preserved": bool(preserve_proposal),
        "order_status": order_status,
    }