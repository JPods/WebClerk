from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from django.db import transaction

from apps.transactions.models import (
    Proposal,
    ProposalLine,
    Order,
    OrderLine,
)
from .transfer_utils import build_line_payload, sum_price_extended

import logging
logger = logging.getLogger(__name__)


class ProposalToOrderTransferError(Exception):
    """Business-rule violation during proposal-to-order transfer."""



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
        'total': float,
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
            "total": 0.0,
        }

    qs = ProposalLine.objects.filter(proposal=proposal)

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

    total_amount = sum_price_extended(qs)

    can_transfer = len(errors) == 0
    return {
        "can_transfer": can_transfer,
        "errors": errors,
        "warnings": warnings,
        "line_count": line_count,
        "total": total_amount,
    }


def _convert_quantity_from_proposal(proposal_qty: Optional[Dict]) -> Dict:
    """Convert proposal line quantity to order line quantity.

    Sets:
      staged  = source remaining (qty being transferred)
      active  = staged (user input — full transfer amount initially)
      remaining = active (no children yet)
      converted_from_proposal = audit trail with original keys

    See: readmes/topics/transactions/transactions-totals.md §2
    """
    q = proposal_qty or {}
    # Use remaining from source (what's available for transfer)
    transfer_qty = q.get("remaining", 0) or q.get("staged", 0) or 0

    converted_from_proposal = {
        "is_blanket": q.get("is_blanket", False),
        "increment": q.get("increment", 0),
        "original_remaining": q.get("remaining", 0),
        "original_staged": q.get("staged", 0),
    }

    order_qty = {
        "staged": transfer_qty,
        "active": transfer_qty,
        "remaining": transfer_qty,
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
    """Transfer proposal lines to a new order (atomic).

    Workflow — collect-then-create pending pattern:
      1. Select lines (all or by ID list)
      2. Create Order header with refs.source.proposal_id
      3. For each ProposalLine:
         a. Convert quantity via _convert_quantity_from_proposal()
         b. Create OrderLine (signal suppressed via _pending_created)
         c. Mark proposal line status = 'transferred' (signal suppressed)
         d. Append inventory delta to pending_deltas array
      4. After all saves, create Pending records from the array
      5. Optionally mark proposal status = 'converted'

    See: readmes/topics/transactions/transactions-totals.md §2
    """
    if not transfer_all and not line_ids:
        raise ProposalToOrderTransferError("Must specify line_ids when transfer_all is False")

    all_lines_qs = ProposalLine.objects.select_for_update().filter(proposal=proposal)
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

    # Copy customer/contact/party fields from proposal to order
    # address_full, email, phone are properties (read from FK records), not settable
    for field in ('customer', 'contact', 'attention',
                  'price_level', 'terms', 'terms_fk'):
        val = getattr(proposal, field, None)
        if val is not None and hasattr(order, field):
            setattr(order, field, val)
    # Copy config (ship_to, etc.)
    if getattr(proposal, 'config', None):
        order.config = dict(proposal.config)
    order.save()

    # ── Build line data for React — NOT saved server-side ────────────
    # Conversion creates the header. React receives line data and populates
    # the form. User reviews, adjusts quantities, clicks Save.
    # Save creates lines + pending records. Pending is fire-and-forget on save.
    lines_for_react = []
    for pl in selected_lines:
        qty = _convert_quantity_from_proposal(getattr(pl, "quantity", None))
        item_data = getattr(pl, "item", None) or {}
        item_id = item_data.get('id') or item_data.get('item_id') if isinstance(item_data, dict) else None

        lines_for_react.append({
            'line_number': getattr(pl, 'line_number', 0) or 0,
            'item': item_data,
            'quantity': qty,
            'price': pl.price or {},
            'cost': getattr(pl, 'cost', None) or {},
            'price_level': getattr(pl, 'price_level', '') or '',
            'status': '',
            'is_active': True,
            'comments': getattr(pl, 'comments', None) or {},
            'config': getattr(pl, 'config', None) or {},
            'commission': getattr(pl, 'commission', None) or {},
            'refs': {
                'source': {'proposal_line_id': pl.id},
                'xfer': build_line_payload(pl, "proposal"),
            },
            '_dirty': True,
        })

    # Proposal lines are NOT modified here. They are only copied.
    # When the user saves the order:
    #   1. OrderLine records are created → each fires on_so pending
    #   2. OrderLine tells ProposalLine how to adjust → ProposalLine saves → fires on_p pending

    return {
        "success": True,
        "order_id": order.id,
        "proposal_id": proposal.id,
        "lines_for_review": len(lines_for_react),
        "lines": lines_for_react,
    }