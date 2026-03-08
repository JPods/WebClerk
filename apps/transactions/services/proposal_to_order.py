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

import logging
logger = logging.getLogger(__name__)


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


def _create_transfer_pending_records(
    order: Order,
    proposal: Proposal,
    pending_deltas: List[Dict],
) -> List:
    """Create Pending records for a proposal → order transfer.

    For each transferred line creates TWO pending records:
      1. Order-side:   on_so += quantity  (new SO commitment)
      2. Proposal-side: on_p -= quantity  (release proposal forecast)

    Called after all lines are saved so IDs are stable.
    """
    from apps.core.models import Pending

    created = []
    for delta in pending_deltas:
        item_id = delta['item_id']
        qty = delta['quantity']

        # 1. Order-side pending: SO commitment
        so_data = {
            'type_id': 'SO',
            'item_num': delta['item_ida'],
            'item_id': item_id,
            'doc_id': getattr(order, 'ida', '') or str(order.pk),
            'doc_pk': order.pk,
            'line_id': delta['order_line_id'],
            'line_num': 0,
            'on_so': qty, 'on_po': 0, 'on_wo': 0,
            'on_in': 0, 'on_r': 0, 'on_p': 0, 'on_hand': 0,
            'unit_cost': delta['unit_cost'],
            'unit_price': delta['unit_price'],
            'reason': 'so line add (from proposal transfer)',
            'take_action': 1,
            'changed_by': '',
            'transaction_type': 'order',
            'transaction_model': 'order',
            'links': {'proposal': {'parent_id': proposal.pk, 'proposal_line_id': delta['proposal_line_id']}},
        }
        p_so = Pending.objects.create(
            model_name='item',
            record_id=str(item_id),
            purpose='inventory_line_add',
            name=f'SO Line Add: {delta["item_ida"]}',
            data=so_data,
        )
        created.append(p_so)

        # 2. Proposal-side pending: release forecast
        pp_data = {
            'type_id': 'PP',
            'item_num': delta['item_ida'],
            'item_id': item_id,
            'doc_id': getattr(proposal, 'ida', '') or str(proposal.pk),
            'doc_pk': proposal.pk,
            'line_id': delta['proposal_line_id'],
            'line_num': 0,
            'on_so': 0, 'on_po': 0, 'on_wo': 0,
            'on_in': 0, 'on_r': 0, 'on_p': -qty, 'on_hand': 0,
            'unit_cost': delta['unit_cost'],
            'unit_price': delta['unit_price'],
            'reason': 'pp transfer to order',
            'take_action': 1,
            'changed_by': '',
            'transaction_type': 'proposal',
            'transaction_model': 'proposal',
            'links': {'order': {'child_id': order.pk, 'order_line_id': delta['order_line_id']}},
        }
        p_pp = Pending.objects.create(
            model_name='item',
            record_id=str(item_id),
            purpose='inventory_line_add',
            name=f'PP Transfer to Order: {delta["item_ida"]}',
            data=pp_data,
        )
        created.append(p_pp)

        logger.debug(
            f"Created pending pair for proposal→order: "
            f"SO#{p_so.pk} (on_so=+{qty}), PP#{p_pp.pk} (on_p=-{qty}) "
            f"item={item_id}"
        )

    return created


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

    # If party_id wasn't accepted at create but exists, set after
    if hasattr(order, "party_id") and proposal_party_id is not None and "party_id" not in order_kwargs:
        try:
            setattr(order, "party_id", proposal_party_id)
            order.save(update_fields=["party_id"])
        except Exception:
            # Ignore if field doesn't exist or is read-only
            pass

    # ── Phase 1: Save all lines, collect inventory deltas ────────────
    line_mapping: Dict[int, int] = {}
    pending_deltas: List[Dict] = []

    for pl in selected_lines:
        qty = _convert_quantity_from_proposal(getattr(pl, "quantity", None))
        ol = OrderLine(
            order=order,
            price=pl.price or {},
            cost=getattr(pl, "cost", None) or {},
            quantity=qty,
            item=getattr(pl, "item", None) or {},
            refs={
                "source": {"proposal_line_id": pl.id},
                "xfer": build_line_payload(pl, "proposal"),  # common payload array
            },
        )
        ol._pending_created = True  # suppress signal
        ol.save()
        line_mapping[pl.id] = ol.id

        # Collect inventory delta for the new order line
        item_data = getattr(pl, 'item', None) or {}
        item_id = item_data.get('id') or item_data.get('item_id') if isinstance(item_data, dict) else None
        staged_qty = float(qty.get('remaining', 0) or qty.get('staged', 0) or qty.get('active', 0) or 0)
        if item_id and staged_qty > 0:
            pending_deltas.append({
                'item_id': item_id,
                'item_ida': item_data.get('ida', str(item_id)) if isinstance(item_data, dict) else str(item_id),
                'quantity': staged_qty,
                'order_line_id': ol.id,
                'proposal_line_id': pl.id,
                'unit_cost': float((getattr(pl, 'cost', None) or {}).get('unit', 0) or 0),
                'unit_price': float((pl.price or {}).get('unit', 0) or 0),
            })

        # Update proposal line: children_active tracker + status
        try:
            pq = dict(getattr(pl, 'quantity', None) or {})
            children = pq.get('children_active', {'sum': 0, 'lines': []})
            if not isinstance(children, dict):
                children = {'sum': 0, 'lines': []}
            if not isinstance(children.get('lines'), list):
                children['lines'] = []
            children['lines'].append({'id': ol.id, 'active': staged_qty})
            children['sum'] = sum(c.get('active', 0) for c in children['lines'])
            pq['children_active'] = children
            p_active = float(pq.get('active', 0) or 0)
            pq['remaining'] = max(0.0, p_active - children['sum'])
            pl.quantity = pq
            pl.status = 'transferred' if pq['remaining'] <= 0 else pl.status
            pl._pending_created = True  # suppress signal
            pl.save(update_fields=['quantity', 'status', 'dt_modified', 'version'])
        except Exception as e:
            logger.warning('Failed to update proposal line %s children_active: %s', pl.pk, e)

    # ── Phase 2: Create pending records from collected deltas ────────
    _create_transfer_pending_records(order, proposal, pending_deltas)

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