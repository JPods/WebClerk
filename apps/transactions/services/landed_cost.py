"""Landed Cost Allocation — spread receipt-header costs across lines.

WC2 pattern: costs entered at the receipt (inshipment) level, allocated
to individual lines/inventory layers proportionally.

Allocation methods:
  - value: cost-proportional (default) — each line's share = line_cost / total_cost
  - weight: weight-proportional — each line's share = line_weight / total_weight
  - quantity: quantity-proportional — each line's share = line_qty / total_qty

After allocation, each ReceiptLine.cost JSON gets freight/duty/handling/vat
fields, and the linked InventoryLayer.cost gets updated via
update_cost_after_receipt().

Usage:
    from apps.transactions.services.landed_cost import allocate_landed_costs
    result = allocate_landed_costs(receipt)
"""
from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

logger = logging.getLogger(__name__)


def allocate_landed_costs(receipt) -> dict:
    """Allocate receipt-header landed costs across all receipt lines.

    Reads receipt.vendor_invoice_freight, .duty, .handling, .vat and
    spreads them across lines using receipt.allocation_method.

    Returns dict with lines_updated count and per-line allocations.
    """
    total_freight = Decimal(str(receipt.vendor_invoice_freight or 0))
    total_duty = Decimal(str(receipt.duty or 0))
    total_handling = Decimal(str(receipt.handling or 0))
    total_vat = Decimal(str(receipt.vat or 0))

    total_landed = total_freight + total_duty + total_handling + total_vat
    if total_landed == 0:
        return {'lines_updated': 0, 'message': 'No landed costs to allocate'}

    lines = list(receipt.lines.select_related('inventory_layer').all())
    if not lines:
        return {'lines_updated': 0, 'message': 'No receipt lines'}

    method = receipt.allocation_method or 'value'

    # ── Compute allocation weights ──
    weights = []
    for line in lines:
        if method == 'weight':
            # Weight from physical JSON or item JSON
            phys = line.physical if isinstance(line.physical, dict) else {}
            item_data = line.item if isinstance(line.item, dict) else {}
            w = float(phys.get('weight', 0) or item_data.get('weight', 0) or 0)
            qty = _get_qty(line)
            weights.append(Decimal(str(w * qty)))
        elif method == 'quantity':
            weights.append(Decimal(str(_get_qty(line))))
        else:
            # value (default) — extended cost
            cost_data = line.cost if isinstance(line.cost, dict) else {}
            ext = float(cost_data.get('extended', 0) or 0)
            if ext == 0:
                unit = float(cost_data.get('unit', 0) or 0)
                ext = unit * _get_qty(line)
            weights.append(Decimal(str(ext)))

    total_weight = sum(weights)
    if total_weight == 0:
        # Fall back to equal distribution
        weights = [Decimal('1')] * len(lines)
        total_weight = Decimal(str(len(lines)))

    # ── Allocate and update ──
    allocations = []
    with transaction.atomic():
        for i, line in enumerate(lines):
            ratio = weights[i] / total_weight

            line_freight = (total_freight * ratio).quantize(Decimal('0.01'), ROUND_HALF_UP)
            line_duty = (total_duty * ratio).quantize(Decimal('0.01'), ROUND_HALF_UP)
            line_handling = (total_handling * ratio).quantize(Decimal('0.01'), ROUND_HALF_UP)
            line_vat = (total_vat * ratio).quantize(Decimal('0.01'), ROUND_HALF_UP)

            qty = Decimal(str(_get_qty(line))) or Decimal('1')
            per_unit_freight = (line_freight / qty).quantize(Decimal('0.0001'), ROUND_HALF_UP)
            per_unit_duty = (line_duty / qty).quantize(Decimal('0.0001'), ROUND_HALF_UP)
            per_unit_handling = (line_handling / qty).quantize(Decimal('0.0001'), ROUND_HALF_UP)
            per_unit_vat = (line_vat / qty).quantize(Decimal('0.0001'), ROUND_HALF_UP)

            # Update ReceiptLine.cost JSON
            cost = line.cost if isinstance(line.cost, dict) else {}
            cost['freight'] = float(line_freight)
            cost['duty'] = float(line_duty)
            cost['handling'] = float(line_handling)
            cost['vat'] = float(line_vat)
            cost['landed_per_unit'] = float(
                Decimal(str(cost.get('unit', 0) or 0))
                + per_unit_freight + per_unit_duty + per_unit_handling + per_unit_vat
            )
            line.cost = cost
            line.save(update_fields=['cost', 'dt_modified'])

            # Update linked InventoryLayer if present
            layer = line.inventory_layer
            if layer:
                unit_po = float(cost.get('unit', 0) or 0)
                layer.update_cost_after_receipt(
                    unit_po,
                    freight=float(per_unit_freight),
                    duty=float(per_unit_duty),
                    handling=float(per_unit_handling),
                    vat=float(per_unit_vat),
                )
                layer.save(update_fields=['cost', 'dt_modified'])

            allocations.append({
                'line_id': line.id,
                'freight': float(line_freight),
                'duty': float(line_duty),
                'handling': float(line_handling),
                'vat': float(line_vat),
                'landed_per_unit': cost['landed_per_unit'],
            })

    logger.info(
        'Landed cost allocated for receipt %s: %s lines, method=%s, '
        'freight=%.2f, duty=%.2f, handling=%.2f, vat=%.2f',
        receipt.ida, len(allocations), method,
        total_freight, total_duty, total_handling, total_vat,
    )

    return {
        'lines_updated': len(allocations),
        'method': method,
        'totals': {
            'freight': float(total_freight),
            'duty': float(total_duty),
            'handling': float(total_handling),
            'vat': float(total_vat),
        },
        'allocations': allocations,
    }


def _get_qty(line) -> float:
    """Extract received quantity from a receipt line."""
    if line.quantity and isinstance(line.quantity, dict):
        return float(
            line.quantity.get('staged', 0)
            or line.quantity.get('received', 0)
            or line.quantity.get('active', 0)
            or 0
        )
    return 0.0
