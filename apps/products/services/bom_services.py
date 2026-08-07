"""Service / domain helpers for BillOfMaterial operations.

These functions encapsulate non-trivial logic (validation orchestration, roll-ups,
filtering, tree expansion, cost propagation, and consume/production) so views remain thin.

Pattern source: WC2 BOM_BuildExtend, BOM_ChildCost, BOM_Consume, BOM_TopLevelLoop, BOM_BuildCalcQty.
"""
from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Iterable
from django.db import transaction
from django.db.models import Q
from apps.products.models.bill_of_material import BillOfMaterial
from apps.products.models.item import Item


# ---------------------------------------------------------------------------
# Existing CRUD operations
# ---------------------------------------------------------------------------

def list_bom_lines(parent_id: int, *, as_of: date | None = None, revision: str | None = None) -> Iterable[BillOfMaterial]:
    """Return BOM lines for a parent filtered by optional effective window and revision."""
    qs = BillOfMaterial.objects.filter(parent_item_id=parent_id).select_related('parent_item', 'child_item')
    if revision is not None:
        qs = qs.filter(revision=revision)
    if as_of:
        qs = qs.filter(
            (Q(dt_effective_from__isnull=True) | Q(dt_effective_from__lte=as_of)) &
            (Q(dt_effective_to__isnull=True) | Q(dt_effective_to__gte=as_of))
        )
    return qs.order_by('sequence', 'id')


@transaction.atomic
def create_bom_line(**data) -> BillOfMaterial:
    line = BillOfMaterial(**data)
    line.full_clean()
    line.save()
    return line


@transaction.atomic
def update_bom_line(line: BillOfMaterial, **data) -> BillOfMaterial:
    for k, v in data.items():
        setattr(line, k, v)
    line.full_clean()
    line.save()
    return line


@transaction.atomic
def delete_bom_line(line: BillOfMaterial) -> None:
    line.delete()


def recalc_parent_cost(parent_id: int) -> None:
    BillOfMaterial.recalc_parent_cost(parent_id)


# ---------------------------------------------------------------------------
# 1. Multi-level tree expansion (BFS)
# ---------------------------------------------------------------------------

@dataclass
class BOMTreeRow:
    """One row in the expanded BOM tree."""
    item_id: int
    item_ida: str
    description: str
    level: int
    qty_plan: Decimal        # qty per ONE parent unit at this level
    qty_actual: Decimal      # total qty needed for the full build
    cost_avg: Decimal = Decimal("0")
    cost_last: Decimal = Decimal("0")
    cost_extended: Decimal = Decimal("0")
    scrap_factor: Decimal = Decimal("0")
    is_subassembly: bool = False


def expand_tree(
    parent_id: int,
    qty: Decimal = Decimal("1"),
    *,
    as_of: date | None = None,
    revision: str | None = None,
    max_depth: int = 20,
    cost_basis: str = 'avg',
) -> list[BOMTreeRow]:
    """BFS expansion of BOM into a flat list with level tracking.

    Each row carries: item info, level depth, qty_plan (per parent unit),
    qty_actual (total needed for the build), and cost fields.

    cost_basis: which cost to use for extended calculation:
      'avg'  — weighted average (accounting, default)
      'last' — most recent receipt (market/current)
      'min'  — minimum of avg and last (conservative quoting)
      'landed' — landed cost including freight/duty
    """
    rows: list[BOMTreeRow] = []
    queue: deque[tuple[int, int, Decimal]] = deque()  # (parent_id, level, cumulative_qty)
    queue.append((parent_id, 0, qty))

    while queue:
        current_parent, level, parent_cum_qty = queue.popleft()
        if level >= max_depth:
            continue

        lines = list_bom_lines(current_parent, as_of=as_of, revision=revision)
        for line in lines:
            qty_plan = line.quantity * (Decimal("1") + line.scrap_factor)
            qty_actual = qty_plan * parent_cum_qty

            # Check if this child is itself an assembly
            has_children = BillOfMaterial.objects.filter(parent_item_id=line.child_item_id).exists()

            # Load costs from child item
            cost_avg = Decimal("0")
            cost_last = Decimal("0")
            child_cost = getattr(line.child_item, 'cost', None)
            if isinstance(child_cost, dict):
                cost_avg = Decimal(str(child_cost.get('avg') or 0))
                cost_last = Decimal(str(child_cost.get('last') or child_cost.get('landed') or 0))

            # Select cost for extended calculation based on cost_basis
            if cost_basis == 'last' and cost_last > 0:
                use_cost = cost_last
            elif cost_basis == 'min':
                candidates = [c for c in (cost_avg, cost_last) if c > 0]
                use_cost = min(candidates) if candidates else cost_avg
            elif cost_basis == 'landed':
                landed = Decimal(str((child_cost or {}).get('landed') or 0))
                use_cost = landed if landed > 0 else cost_avg
            else:
                use_cost = cost_avg

            row = BOMTreeRow(
                item_id=line.child_item_id,
                item_ida=line.child_ida or str(line.child_item_id),
                description=line.child_description or '',
                level=level + 1,
                qty_plan=qty_plan,
                qty_actual=qty_actual,
                cost_avg=cost_avg,
                cost_last=cost_last,
                cost_extended=qty_plan * use_cost,
                scrap_factor=line.scrap_factor,
                is_subassembly=has_children,
            )
            rows.append(row)

            # If sub-assembly, recurse into its children
            if has_children:
                queue.append((line.child_item_id, level + 1, qty_actual))

    return rows


# ---------------------------------------------------------------------------
# 2. Multi-level cost propagation
# ---------------------------------------------------------------------------

def propagate_cost_up(item_id: int, max_depth: int = 20) -> list[int]:
    """Recalculate cost for all ancestor assemblies when a component cost changes.

    Walks UP from the given item through all parents, recalculating each.
    Returns list of parent item IDs that were recalculated.
    """
    recalculated: list[int] = []
    queue: deque[int] = deque([item_id])
    visited: set[int] = set()
    depth = 0

    while queue and depth < max_depth:
        current_id = queue.popleft()
        if current_id in visited:
            continue
        visited.add(current_id)

        # Find all parents that use this item as a component
        parent_ids = list(
            BillOfMaterial.objects.filter(child_item_id=current_id)
            .values_list('parent_item_id', flat=True)
            .distinct()
        )
        for pid in parent_ids:
            if pid not in visited:
                recalc_parent_cost(pid)
                recalculated.append(pid)
                queue.append(pid)
        depth += 1

    return recalculated


# ---------------------------------------------------------------------------
# 3. Consume / produce (assembly production transaction)
# ---------------------------------------------------------------------------

@transaction.atomic
def consume_bom(
    parent_item_id: int,
    qty: Decimal,
    *,
    adjust_for_on_hand: bool = False,
    reason: str = "BOM assembly",
    as_of: date | None = None,
    revision: str | None = None,
) -> dict:
    """Post inventory movements for a BOM assembly build.

    Consumes child components via FIFO/LIFO (proper layer drain with cost),
    sums the total component cost, then receipts the parent as a new layer
    at unit_cost = total_component_cost / qty_built.

    The new parent layer is weighted-averaged into the parent's existing
    inventory by create_layer → recalc_average_cost.

    Returns dict with batch_id, build_cost, unit_cost, movements count.
    """
    from apps.products.services.inventory_services import (
        consume_by_item_method, create_layer,
    )
    from apps.products.models.warehouse import Warehouse

    parent = Item.objects.get(id=parent_item_id)
    batch_id = str(uuid.uuid4())
    total_component_cost = Decimal("0")
    movement_count = 0

    # 1. Consume each child component using proper layer drain
    lines = list_bom_lines(parent_item_id, as_of=as_of, revision=revision)
    for line in lines:
        qty_plan = line.quantity * (Decimal("1") + line.scrap_factor)
        qty_to_consume = qty_plan * qty

        if adjust_for_on_hand:
            on_hand = _get_on_hand(line.child_item_id)
            qty_to_consume = calc_net_build_qty(qty_to_consume, on_hand)
            if qty_to_consume <= 0:
                continue

        child_cost, _child_batch = consume_by_item_method(
            line.child_item_id,
            qty_to_consume,
            reason=f"BOM build {batch_id[:8]} for {parent.ida or parent_item_id}",
            source_doc_type="bom_build",
        )
        total_component_cost += child_cost
        movement_count += 1

    # 2. Calculate unit cost for the built assembly
    unit_cost = total_component_cost / qty if qty > 0 else Decimal("0")

    # 3. Receipt the parent as a new inventory layer at the build cost
    #    create_layer handles: layer creation, cost recording, receipt movement,
    #    and recalc_average_cost (weighted average into existing inventory)
    default_wh = Warehouse.objects.filter(is_active=True).first()
    if default_wh:
        create_layer(
            item_id=parent_item_id,
            warehouse_id=default_wh.id,
            qty=qty,
            unit_cost=unit_cost,
            source_doc_type="bom_build",
            lot=f"build-{batch_id[:8]}",
            reason=f"{reason} (batch {batch_id[:8]})",
        )
        movement_count += 1

    return {
        "batch_id": batch_id,
        "build_cost": float(total_component_cost),
        "unit_cost": float(unit_cost),
        "movements": movement_count,
        "qty_built": float(qty),
    }


# ---------------------------------------------------------------------------
# 4. Where-used: find top-level assemblies
# ---------------------------------------------------------------------------

def find_top_level_assemblies(child_item_id: int, max_depth: int = 20) -> list[int]:
    """Walk UP the BOM from a child to find all root assemblies (items with no parents).

    Returns list of top-level item IDs. Useful for impact analysis when a
    component price changes or availability drops.
    """
    top_levels: list[int] = []
    queue: deque[int] = deque([child_item_id])
    visited: set[int] = set()

    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)

        parent_ids = list(
            BillOfMaterial.objects.filter(child_item_id=current)
            .values_list('parent_item_id', flat=True)
            .distinct()
        )
        if not parent_ids:
            # This item has no parents — it IS a top-level assembly
            if current != child_item_id:  # don't include the starting item
                top_levels.append(current)
        else:
            for pid in parent_ids:
                if pid not in visited and len(visited) < max_depth * 10:
                    queue.append(pid)

    return top_levels


# ---------------------------------------------------------------------------
# 5. Net build quantity calculator
# ---------------------------------------------------------------------------

def calc_net_build_qty(qty_requested: Decimal, qty_on_hand: Decimal) -> Decimal:
    """Given requested qty and on-hand, return how much actually needs to be built/consumed.

    If on_hand covers the request, nothing needs to be built (returns 0).
    Otherwise returns the shortfall.

    Source: WC2 BOM_BuildCalcQty — handles all sign combinations.
    """
    if qty_requested <= 0:
        return Decimal("0")
    if qty_on_hand >= qty_requested:
        return Decimal("0")
    return qty_requested - max(qty_on_hand, Decimal("0"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_on_hand(item_id: int) -> Decimal:
    """Get current on-hand quantity for an item. Returns 0 if not available."""
    try:
        from apps.products.models.inventory_layer import SiteInventory
        total = SiteInventory.objects.filter(item_id=item_id).values_list('quantity', flat=True)
        return sum((Decimal(str(q)) for q in total), Decimal("0"))
    except Exception:
        return Decimal("0")


__all__ = [
    'list_bom_lines', 'create_bom_line', 'update_bom_line', 'delete_bom_line',
    'recalc_parent_cost', 'expand_tree', 'propagate_cost_up', 'consume_bom',
    'find_top_level_assemblies', 'calc_net_build_qty', 'BOMTreeRow',
]
