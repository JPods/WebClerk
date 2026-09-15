# Bill of Materials — Operations Guide
**Built:** 2026-07-04 | **Source:** WC2 BOM mining + 4D best practices

---

## Overview

The BOM system lets you define assemblies (kits, bundles, manufactured items) as a parent item with child components. Any item can be both a parent and a child — enabling multi-level BOMs where a sub-assembly is itself made of parts.

**Live example:** BB200 (Baseball Kit) contains 7 components including BB404 (WS Baseball Starter Inventory) which is itself a sub-assembly with 3 children.

---

## Data Model

```
Item (any item can be a parent or child)
  └── BillOfMaterial (junction table — one row per component)
       ├── parent_item  → Item FK (the assembly)
       ├── child_item   → Item FK (the component)
       ├── quantity     → how many of child per ONE parent
       ├── scrap_factor → waste ratio (0-1), applied as qty × (1 + scrap)
       ├── sequence     → display/build order
       ├── revision     → version code (optional)
       ├── dt_effective_from / dt_effective_to → date window
       ├── is_alternate + alternate_group → substitution groups
       ├── is_optional  → not required for build
       ├── cost_snapshot → unit cost captured at creation time
       └── op_data      → JSON for routing/tooling notes
```

**Constraints:**
- Parent cannot equal child (self-reference blocked)
- Cycle detection: adding A→B is blocked if B→...→A exists anywhere in the tree
- Unique constraint: one BOM line per parent+child pair
- Scrap factor must be 0 ≤ x < 1

---

## API Endpoints

All endpoints require authentication.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/products/items/{parent_id}/bom/` | GET | List single-level BOM lines |
| `/products/items/{parent_id}/bom/` | POST | Add a component to an assembly |
| `/products/items/{parent_id}/bom/expand/?qty=N` | GET | Multi-level tree expansion (flat with levels) |
| `/products/items/{parent_id}/bom/recalc-cost/` | POST | Recalculate single parent cost from components |
| `/products/items/{parent_id}/bom/consume/` | POST | Build: post +parent, -children to inventory |
| `/products/items/{item_id}/bom/where-used/` | GET | Find all top-level assemblies containing this item |
| `/products/items/{item_id}/bom/propagate-cost/` | POST | Recalc cost up through ALL ancestor assemblies |
| `/products/bom/{pk}/` | GET/PATCH/DELETE | Single BOM line detail |

### Query Parameters

- `as_of=YYYY-MM-DD` — resolve BOM at a historical date (effective window filtering)
- `revision=REV` — select a specific BOM revision
- `qty=N` — build quantity for expand (affects qty_actual calculations)

---

## Core Operations

### 1. Expand Tree

Returns the full multi-level BOM as a flat list with depth tracking.

```
GET /products/items/244/bom/expand/?qty=10
```

Response:
```json
{
  "rows": [
    {"item_id": 250, "item_ida": "BB005", "description": "Baseball - Wilson",
     "level": 1, "qty_plan": 3.0, "qty_actual": 30.0,
     "cost_avg": 1.15, "cost_last": 0.0, "cost_extended": 3.44,
     "scrap_factor": 0.0, "is_subassembly": false},
    {"item_id": 252, "item_ida": "BB404", "description": "WS Baseball Starter Inventory",
     "level": 1, "qty_plan": 3.0, "qty_actual": 30.0,
     "cost_avg": 59.93, "cost_last": 0.0, "cost_extended": 179.78,
     "scrap_factor": 0.0, "is_subassembly": true},
    {"item_id": 240, "item_ida": "BBF", "description": "Foam Seamed Baseballs",
     "level": 2, "qty_plan": 3.0, "qty_actual": 90.0,
     "cost_avg": 0.0, "cost_last": 0.0, "cost_extended": 0.0,
     "scrap_factor": 0.0, "is_subassembly": false}
  ],
  "total_cost": 269.30,
  "total_rows": 15
}
```

- `qty_plan` = per ONE parent unit
- `qty_actual` = total needed for the full build (qty_plan × build qty × all parent multipliers)
- `is_subassembly` = true means this row has its own children (expandable in tree UI)

### 2. Cost Rollup

Two modes:

**Single parent recalc:**
```
POST /products/items/244/bom/recalc-cost/
```
Recomputes `item.cost.components.snapshot_total` from direct children only.

**Propagate up (cascade):**
```
POST /products/items/250/bom/propagate-cost/
```
When BB005's cost changes, this walks UP through all assemblies that contain it (BB200) and recalculates each. Returns which parents were recalculated.

### 3. Consume / Build

Post inventory movements for an assembly production run:
```
POST /products/items/244/bom/consume/
{"qty": 5, "adjust_for_on_hand": true, "reason": "Production run #47"}
```

Creates:
- +5 InventoryMovement (receipt) for BB200
- -15 InventoryMovement (issue) for BB005 (5 × 3)
- -10 for BB100 (5 × 2)
- -10 for BB101 (5 × 2)
- ...etc for each component

All tagged with the same `batch_id` UUID for traceability.

`adjust_for_on_hand=true`: if you have 10 BB005 on hand and need 15, only consume the net 5 needed (doesn't touch the other 10).

### 4. Where-Used

Impact analysis: "which assemblies will be affected if this component changes?"
```
GET /products/items/250/bom/where-used/
```

Returns:
```json
{
  "top_level_assemblies": [{"id": 244, "ida": "BB200", "description": "Baseball Kit"}],
  "total": 1
}
```

---

## Cost System

Three cost values are available per component:

| Cost | Source | Use Case |
|------|--------|----------|
| `cost_avg` | Item.cost.avg | Accounting — rolling average of what you've paid |
| `cost_last` | Item.cost.last | Market — most recent receipt price |
| `cost_snapshot` | BOM line field | Historical — what the cost was when the BOM was defined |

**Current behavior:** `recalc_parent_cost` uses cost_snapshot (falls back to avg→standard→last→landed from Item.cost JSON).

**Future:** Three-cost forecast options (min-of-all, min-matrix-last, matrix-only) for quoting vs accounting vs procurement.

---

## DataBrowser Display

The BOM displays in DataGrid using tree mode:

```typescript
<DataGrid
  records={expandTreeResponse.rows}
  treeColumn="item_ida"      // this column gets indent + ▶/▼ chevron
  levelField="level"         // depth from expand_tree
  childFlag="is_subassembly" // which rows are expandable
  columns={['item_ida', 'description', 'qty_plan', 'qty_actual', 'cost_avg', 'cost_extended']}
/>
```

- Same columns at every level — recursive by data
- Click ▶/▼ to expand/collapse sub-assemblies inline
- Shift-click a sub-assembly → opens new DataBrowser window for that assembly's BOM

---

## BB200 Example (Live)

```
BB200  Baseball Kit                         $269.30 component cost
├── BB005   Baseball - Wilson          x3   @ $1.15  = $3.44
├── BB100   Fielders Glove-Wilson      x2   @ $11.01 = $22.03
├── BB101   Little League Bat          x2   @ $7.78  = $15.56
├── BB102   Batting Glove, Saranac     x4   @ $4.96  = $19.84
├── BB103   Batting Glove-Wilson       x4   @ $2.17  = $8.66
├── BB105   Little League Baseballs    x5   @ $4.00  = $20.00
└── BB404   WS Baseball Starter Inv.   x3   @ $59.93 = $179.78  [SUB-ASSEMBLY]
     ├── BBF    Foam Seamed Baseballs   x3   @ $0     = $0
     ├── BBK    Dozen Kapok Baseballs   x3   @ $0     = $0
     └── BBPV   Ventilated Poly BB      x3   @ $0     = $0
```

---

## Service Functions (Python)

```python
from apps.products.services.bom_services import (
    list_bom_lines,            # single-level query with as_of/revision filtering
    create_bom_line,           # add component (validates cycles)
    update_bom_line,           # modify qty/scrap/sequence
    delete_bom_line,           # remove component
    expand_tree,               # multi-level BFS expansion
    recalc_parent_cost,        # single parent cost rollup
    propagate_cost_up,         # cascade recalc up all ancestors
    consume_bom,               # post inventory movements for a build
    find_top_level_assemblies, # where-used impact analysis
    calc_net_build_qty,        # net requested vs on-hand
)
```

---

## Files

| File | Purpose |
|------|---------|
| `apps/products/models/bill_of_material.py` | Model + cycle detection + recalc_parent_cost |
| `apps/products/services/bom_services.py` | All BOM operations (expand, consume, propagate, where-used) |
| `apps/products/views/bom_views.py` | API endpoints |
| `apps/products/urls.py` | URL routing |
| `apps/products/serializers/bom_serializers.py` | DRF serializer |
| `apps/products/tests/test_bom_api.py` | API tests |
| `apps/products/management/commands/seed_sample_bom.py` | Sample data seeder |
