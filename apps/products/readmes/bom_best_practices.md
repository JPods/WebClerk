# Bill of Materials (BOM) - Best Practices & Implementation Plan

## Overview

This document outlines the modernization plan for Bill of Materials functionality in webClerk3, derived from legacy 4D implementation analysis and modern best practices.

---

## Current State Analysis

### Existing wc3 Model (`bill_of_material.py`)

**Strengths:**
- ✅ Parent/Component FK relationship with proper indexes
- ✅ Cycle detection (`_would_create_cycle`, `_descendant_component_ids`)
- ✅ Revision & effective date windowing (`revision`, `dt_effective_from`, `dt_effective_to`)
- ✅ Scrap factor & yield percentage support
- ✅ Alternate/substitute component grouping (`is_alternate`, `alternate_group`)
- ✅ Cost snapshot capture on create
- ✅ Unique constraint preventing duplicate parent+component
- ✅ Self-reference prevention constraint

**Gaps Identified from 4D Legacy:**
- ❌ No multi-level BOM explosion (4D: `BOM_BuildExtend`)
- ❌ No inventory consumption/build workflow (4D: `BOM_Consume`)
- ❌ No cost roll-up across all levels (4D: `BOM_ExtendCost`, `BOM_ChildCost`)
- ❌ No "where-used" / top-level parent finder (4D: `BOM_TopLevel`, `BOM_TopLevelLoop`)
- ❌ No quantity-on-hand aware building (4D: `BOM_BuildCalcQty`)
- ❌ No BOM change history/audit table (4D: `AcceptBOM` → `DBOM` table)
- ❌ No price matrix integration for quantity-based costing

---

## Legacy 4D Functions Reference

| 4D Method | Purpose | Priority | wc3 Status |
|-----------|---------|----------|------------|
| `BOM_DoBOM` | Entry point - builds single or multi-level BOM | HIGH | ❌ Missing |
| `BOM_BuildExtend` | Multi-level BOM explosion with depth tracking | HIGH | ❌ Missing |
| `BOM_Consume` | Consume components & adjust inventory for build | HIGH | ❌ Missing |
| `BOM_CostMatrix` | Calculate costs using price matrix by qty | MEDIUM | ❌ Missing |
| `BOM_CostItems` | Calculate avg/last costs for BOM lines | MEDIUM | Partial |
| `BOM_ExtendCost` | Roll-up costs across multi-level BOM | HIGH | ❌ Missing |
| `BOM_ChildCost` | Recursive child cost calculation | MEDIUM | ❌ Missing |
| `BOM_TopLevel` | Find all assemblies using an item | MEDIUM | ❌ Missing |
| `BOM_TopLevelLoop` | Loop helper for parent discovery | MEDIUM | ❌ Missing |
| `BOM_CheckLoop` | Prevent circular references | HIGH | ✅ Done |
| `BOM_FillArray` | Populate display arrays for UI | LOW | N/A (API) |
| `BOM_BuildCalcQty` | Calculate build qty considering on-hand | MEDIUM | ❌ Missing |
| `BOM_QtyChange` | Handle qty adjustments | MEDIUM | ❌ Missing |
| `AcceptBOM` | Audit/history on BOM changes | MEDIUM | ❌ Missing |
| `Bom_Export` | Export BOM data | LOW | ❌ Missing |

---

## Implementation Plan

### Phase 1: Core BOM Explosion Services (HIGH Priority)

#### 1.1 Multi-Level BOM Explosion

```python
# apps/products/services/bom_services.py

def explode_bom(
    parent_item_id: int,
    *,
    quantity: Decimal = Decimal("1"),
    as_of: date | None = None,
    revision: str | None = None,
    max_depth: int = 20,
    include_alternates: bool = False,
) -> list[BOMExplosionLine]:
    """
    Explode a multi-level BOM returning all components at all levels.
    
    Returns list of BOMExplosionLine with:
    - item_id, component_id
    - level (depth in tree)
    - quantity_per (qty at this BOM point)
    - quantity_extended (qty needed for parent qty)
    - scrap_factor, yield_pct
    - unit_cost, extended_cost
    - path (list of item_ids from root to this component)
    """
```

#### 1.2 Where-Used (Reverse BOM)

```python
def where_used(
    component_item_id: int,
    *,
    max_depth: int = 20,
    as_of: date | None = None,
) -> list[WhereUsedLine]:
    """
    Find all assemblies that use a component (direct and indirect).
    
    Returns list showing:
    - parent_item_id, parent_item_ida
    - level (distance from queried component)
    - quantity_per
    - path to top-level
    """
```

---

### Phase 2: Inventory Integration (HIGH Priority)

#### 2.1 BOM Consumption (Build Assembly)

```python
# apps/products/services/bom_build_service.py

@dataclass
class BOMBuildResult:
    parent_item_id: int
    quantity_built: Decimal
    total_cost: Decimal
    adjustments: list[InventoryAdjustment]
    shortages: list[ComponentShortage]

def build_assembly(
    parent_item_id: int,
    quantity: Decimal,
    *,
    location_id: int | None = None,
    adjust_for_on_hand: bool = False,
    consume_components: bool = True,
    create_parent_inventory: bool = True,
    reference_type: str = "BOM_BUILD",
    reference_id: int | None = None,
) -> BOMBuildResult:
    """
    Build an assembly by consuming components and creating parent inventory.
    
    Legacy 4D: BOM_Consume
    
    Steps:
    1. Explode BOM to get all required components
    2. Check component availability (optional)
    3. Calculate adjusted build qty if adjust_for_on_hand=True
    4. Create inventory adjustments for component consumption
    5. Create inventory adjustment for parent production
    6. Return result with cost roll-up
    """
```

#### 2.2 Availability Check

```python
def check_build_availability(
    parent_item_id: int,
    quantity: Decimal,
    *,
    location_id: int | None = None,
    as_of: date | None = None,
) -> BuildAvailabilityResult:
    """
    Check if sufficient components exist to build requested quantity.
    
    Returns:
    - can_build: bool
    - max_buildable: Decimal
    - shortages: list of {component_id, required, available, short}
    """
```

---

### Phase 3: Cost Roll-Up Services (MEDIUM Priority)

#### 3.1 Multi-Level Cost Calculation

```python
@dataclass
class BOMCostResult:
    parent_item_id: int
    total_standard_cost: Decimal
    total_avg_cost: Decimal
    total_last_cost: Decimal
    component_breakdown: list[ComponentCostLine]
    
def calculate_bom_cost(
    parent_item_id: int,
    quantity: Decimal = Decimal("1"),
    *,
    cost_type: Literal["standard", "avg", "last", "matrix"] = "avg",
    as_of: date | None = None,
    revision: str | None = None,
) -> BOMCostResult:
    """
    Calculate total cost for a BOM considering all levels.
    
    Legacy 4D: BOM_CostMatrix, BOM_ExtendCost, Bom_CostItems
    
    Supports:
    - Standard cost
    - Average cost
    - Last receipt cost
    - Price matrix lookup (qty-based costing)
    """
```

#### 3.2 Cost Roll-Up to Parent Item

```python
def rollup_bom_cost_to_item(
    parent_item_id: int,
    *,
    update_item_cost: bool = False,
) -> Decimal:
    """
    Roll-up component costs and optionally update parent Item.cost JSON.
    
    Updates: Item.cost['components']['snapshot_total']
    Optionally promotes to Item.cost['avg'] if unset.
    """
```

---

### Phase 4: Audit & History (MEDIUM Priority)

#### 4.1 BOM Change History Model

```python
# apps/products/models/bom_history.py

class BOMHistory(BaseModel):
    """Audit trail for BOM changes (mirrors 4D DBOM table)."""
    
    bom_line = models.ForeignKey(BillOfMaterial, on_delete=models.SET_NULL, null=True)
    
    # Snapshot of values at change time
    item_parent = models.CharField(max_length=120)
    item_child = models.CharField(max_length=120)
    item_parent_new = models.CharField(max_length=120)
    item_child_new = models.CharField(max_length=120)
    quantity_old = models.DecimalField(...)
    quantity_new = models.DecimalField(...)
    
    change_type = models.CharField(...)  # CREATE, UPDATE, DELETE
    change_reason = models.CharField(...)
    changed_by = models.ForeignKey(User, ...)
    changed_at = models.DateTimeField(auto_now_add=True)
```

#### 4.2 Signal-Based History Capture

```python
# apps/products/signals.py

@receiver(pre_save, sender=BillOfMaterial)
def capture_bom_history_on_save(sender, instance, **kwargs):
    """Auto-capture BOM changes to history table."""

@receiver(pre_delete, sender=BillOfMaterial)
def capture_bom_history_on_delete(sender, instance, **kwargs):
    """Record deletion in history."""
```

---

### Phase 5: API Endpoints

#### Proposed Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/items/{id}/bom/` | List direct BOM lines for item |
| GET | `/api/items/{id}/bom/explode/` | Multi-level BOM explosion |
| GET | `/api/items/{id}/bom/where-used/` | Reverse BOM lookup |
| GET | `/api/items/{id}/bom/cost/` | Calculate BOM cost |
| GET | `/api/items/{id}/bom/availability/` | Check build availability |
| POST | `/api/items/{id}/bom/build/` | Execute assembly build |
| POST | `/api/bom/` | Create BOM line |
| PATCH | `/api/bom/{id}/` | Update BOM line |
| DELETE | `/api/bom/{id}/` | Delete BOM line |
| GET | `/api/bom/{id}/history/` | BOM line change history |

---

## Data Structures

### BOM Explosion Response

```json
{
  "parent_item_id": 123,
  "parent_item_ida": "WIDGET-ASSY",
  "quantity": 10,
  "as_of": "2026-02-04",
  "lines": [
    {
      "level": 1,
      "item_id": 456,
      "item_ida": "PART-A",
      "description": "Component Part A",
      "quantity_per": 2.0,
      "quantity_extended": 20.0,
      "scrap_factor": 0.05,
      "unit_cost": 5.25,
      "extended_cost": 110.25,
      "path": [123, 456],
      "is_leaf": true
    },
    {
      "level": 1,
      "item_id": 789,
      "item_ida": "SUB-ASSY-B",
      "description": "Sub-Assembly B",
      "quantity_per": 1.0,
      "quantity_extended": 10.0,
      "scrap_factor": 0.0,
      "unit_cost": 25.00,
      "extended_cost": 250.00,
      "path": [123, 789],
      "is_leaf": false
    },
    {
      "level": 2,
      "item_id": 999,
      "item_ida": "PART-C",
      "description": "Component in Sub-Assembly",
      "quantity_per": 3.0,
      "quantity_extended": 30.0,
      "scrap_factor": 0.02,
      "unit_cost": 1.10,
      "extended_cost": 33.66,
      "path": [123, 789, 999],
      "is_leaf": true
    }
  ],
  "totals": {
    "total_cost": 393.91,
    "leaf_count": 2,
    "max_depth": 2
  }
}
```

---

## Migration Considerations

### From 4D Legacy

1. **BOM Table** → `BillOfMaterial` model (largely done)
2. **DBOM Table** → `BOMHistory` model (new)
3. **Array-based UI logic** → API responses (N/A for backend)
4. **Process variables** → Service function parameters

### Testing Strategy

1. **Unit tests** for each service function
2. **Cycle detection tests** (circular BOM prevention)
3. **Cost calculation accuracy tests** (compare with 4D outputs)
4. **Inventory adjustment integration tests**
5. **Performance tests** for deep BOMs (20+ levels)

---

## File Structure

```
apps/products/
├── models/
│   ├── bill_of_material.py      # ✅ Exists
│   └── bom_history.py           # 🆕 New
├── services/
│   ├── bom_services.py          # ✅ Exists (extend)
│   ├── bom_explosion.py         # 🆕 New
│   ├── bom_build_service.py     # 🆕 New
│   └── bom_cost_service.py      # 🆕 New
├── serializers/
│   └── bom_serializers.py       # 🆕 New
├── views/
│   └── bom_views.py             # 🆕 New
└── tests/
    └── test_bom_services.py     # 🆕 New
```

---

## Priority Order

1. **Phase 1.1**: Multi-level BOM explosion ← *Start here*
2. **Phase 2.1**: Build assembly with consumption
3. **Phase 3.1**: Cost calculation
4. **Phase 1.2**: Where-used
5. **Phase 4**: History/audit
6. **Phase 5**: API endpoints
7. **Phase 6**: Demand forecasting (future)

---

## Phase 6: Demand Forecasting / MRP (FUTURE)

> **Status:** Stubbed — requires Phase 1 (BOM explosion) as prerequisite

### Concept

Forecast component demand by aggregating:

1. **Proposals** × probability weight → expected demand by expected close date
2. **Sales Orders** → firm demand by ship date  
3. **Purchase Orders** → expected supply by receive date

Explode all through BOM to calculate **net component requirements** over time.

### Proposed Service Interface

```python
# apps/products/services/demand_forecast_service.py

@dataclass
class ForecastBucket:
    period_start: date
    period_end: date
    gross_demand: Decimal      # From orders + weighted proposals
    scheduled_receipts: Decimal # From POs
    projected_on_hand: Decimal
    net_requirement: Decimal
    
@dataclass 
class ComponentForecast:
    item_id: int
    item_ida: str
    current_on_hand: Decimal
    buckets: list[ForecastBucket]
    
def forecast_component_demand(
    item_ids: list[int] | None = None,  # None = all items
    *,
    horizon_days: int = 90,
    bucket_size: Literal["day", "week", "month"] = "week",
    include_proposals: bool = True,
    proposal_min_probability: Decimal = Decimal("0.25"),
    explode_bom: bool = True,
) -> list[ComponentForecast]:
    """
    Calculate time-phased demand forecast for components.
    
    Steps:
    1. Query proposals with probability >= threshold, group by expected date
    2. Query open sales orders, group by ship date
    3. Query open POs, group by receive date
    4. Explode parent items through BOM to leaf components
    5. Time-phase into buckets
    6. Calculate net requirements (demand - supply - on_hand)
    """
```

### Data Sources

| Source | Demand/Supply | Date Field | Weight |
|--------|---------------|------------|--------|
| `Proposal` | Demand | `expected_close_date` | `probability` (0-1) |
| `SalesOrder` | Demand | `ship_date` | 1.0 (firm) |
| `SalesOrderLine` | Demand | Line-level ship date | 1.0 |
| `PurchaseOrder` | Supply | `receive_date` | 1.0 |
| `PurchaseOrderLine` | Supply | Line-level receive date | 1.0 |

### Output Example

```json
{
  "forecast_date": "2026-02-04",
  "horizon_days": 90,
  "bucket_size": "week",
  "components": [
    {
      "item_id": 456,
      "item_ida": "PART-A",
      "current_on_hand": 100,
      "buckets": [
        {
          "period_start": "2026-02-03",
          "period_end": "2026-02-09",
          "gross_demand": 45.0,
          "scheduled_receipts": 0,
          "projected_on_hand": 55.0,
          "net_requirement": 0
        },
        {
          "period_start": "2026-02-10",
          "period_end": "2026-02-16",
          "gross_demand": 80.0,
          "scheduled_receipts": 50.0,
          "projected_on_hand": 25.0,
          "net_requirement": 0
        },
        {
          "period_start": "2026-02-17",
          "period_end": "2026-02-23",
          "gross_demand": 120.0,
          "scheduled_receipts": 0,
          "projected_on_hand": -95.0,
          "net_requirement": 95.0
        }
      ]
    }
  ]
}
```

### Dependencies

- ✅ `BillOfMaterial` model
- ⏳ BOM explosion service (Phase 1)
- 🔗 `Proposal` model (apps.transactions)
- 🔗 `SalesOrder` / `SalesOrderLine` models
- 🔗 `PurchaseOrder` / `PurchaseOrderLine` models

### Future Enhancements

- Safety stock consideration
- Lead time offsetting
- Reorder point suggestions
- Auto-generate PO recommendations

---

## References

- Legacy 4D Source: `/00WebClerk19/Project/Sources/Methods/BOM_*.4dm`
- Current Model: [bill_of_material.py](../models/bill_of_material.py)
- Current Services: [bom_services.py](../services/bom_services.py)
