# Work Orders: flow of goods through factory processes

<!-- TOC START -->

## Table of Contents

- [Work Orders: flow of goods through factory processes](#work-orders-flow-of-goods-through-factory-processes)
  - [Table of Contents](#table-of-contents)
  - [Why this shape](#why-this-shape)
  - [Canonical fields (initial)](#canonical-fields-initial)
  - [Status flow (suggested)](#status-flow-suggested)
  - [QuestionAnswer and traceability](#question_answer-and-traceability)
  - [JSON envelope examples](#json-envelope-examples)
    - [GET filtering examples](#get-filtering-examples)
  - [Implementation phases](#implementation-phases)
  - [Minimal DB model sketch (later)](#minimal-db-model-sketch-later)
  - [Open questions](#open-questions)
  - [Next steps](#next-steps)
  - [Admin quick actions](#admin-quick-actions)

<!-- TOC END -->

This proposal outlines a lightweight, ops-first way to manage manufacturing flow using two core entities:

- WorkOrder: the order to produce/repair/inspect a parent item or assembly.
- WorkOrderLine: process steps and material/operation breakdowns that move a WorkOrder from planned to complete.

Both should be linkable to QuestionAnswer inspections and to Documents and Linkages for traceability and actions.

## Why this shape

- Clear separation of the header (WorkOrder) and the steps/consumption (WorkOrderLine)
- Works with the existing JSON envelope pattern (metadata, refs, prefs, comments)
- Compatible with existing universal API and search semantics
- Seamless cross-linking to QuestionAnswer, Linkage, and Document models without schema churn

## Canonical fields (initial)

WorkOrder (header):

- id (db primary key)
- org_id (optional)
- item_id (the primary item/assembly)
- quantity, uom
- status: planned | released | in_progress | hold | complete | canceled
- scheduled_start, scheduled_end (optional)
- actual_start, actual_end (optional)
- refs: { qa_ids: [], doc_ids: [], link_ids: [], related_order_ids: [], ... }
- metadata: { routing_hint, priority, workstation, lot, serials, ... }
- prefs: { auto_numbering, allow_partial_complete, quality_gates: [], ... }
- comments: []

WorkOrderLine (detail/steps):

- id
- workorder_id (FK to WorkOrder)
- sequence (integer for ordering)
- process (name/key), station (optional)
- item_id (component/material if backflushing or kitting)
- qty_required, qty_issued, qty_scrap
- status: planned | in_progress | done | skipped | rework
- refs: { qa_ids: [], doc_ids: [], link_ids: [], ... }
- metadata: { setup_time_min, run_time_min, operator, instructions, ... }
- prefs: { backflush: true/false, requires_qa_gate: true/false, ... }
- comments: []

Notes:

- id is the authoritative local identity; uuid can be derived/reserved for cross-system use if needed.
- This fits with the project’s policy: use id for intra-DB joins; reserve uuid for cross-database identity.

## Status flow (suggested)

WorkOrder:

- planned -> released -> in_progress -> complete
- planned -> canceled
- Any active -> hold -> in_progress

WorkOrderLine:

- planned -> in_progress -> done
- planned -> skipped
- in_progress -> rework -> done

Enforced in code:

- WorkOrder: transitions validated in model save() with a completion guard that requires all lines to be `done` before the header can move to `complete`.
- WorkOrderLine: transitions validated in model save(); empty/None status defaults to `planned`.

These can be enforced initially in code (validators/clean methods) and refined later.

## QuestionAnswer and traceability

- QuestionAnswer: Attach QuestionAnswer records at either the header or line via refs.qa_ids. Use the existing QuestionAnswer endpoints.
- Linkage: Connect related transactions (e.g., requisitions, POs for components, service vouchers) via the Linkage model.
- Documents: Attach instructions, SOPs, checklists via the Document model. Store doc_ids in refs; search indexes pick these up.

## JSON envelope examples

Create a WorkOrder (header):

```json
{
  "model_name": "workorder",
  "record": {
    "item_id": 101,
    "quantity": 50,
    "uom": "ea",
    "status": "planned",
    "metadata": {
      "routing_hint": "assy-line-1",
      "priority": 2
    },
    "refs": {
      "qa_ids": [],
      "doc_ids": [],
      "link_ids": []
    },
    "prefs": { "allow_partial_complete": true },
    "comments": ["Initial release"]
  }
}
```

Create WorkOrderLines:

```json
{
  "model_name": "workorder_line",
  "records": [
    {
      "workorder_id": 1,
      "sequence": 10,
      "process": "kit-components",
      "status": "planned",
      "metadata": { "instructions": "Pick list A" }
    },
    {
      "workorder_id": 1,
      "sequence": 20,
      "process": "assembly",
      "station": "assy-1",
      "status": "planned",
      "prefs": { "requires_qa_gate": true }
    }
  ]
}
```

Attach QuestionAnswer to a line (or header):

```json
{
  "model_name": "workorder_line",
  "record": {
    "id": 2,
    "refs": { "qa_ids": [555] }
  }
}
```

Add a document link to the header:

```json
{
  "model_name": "workorder",
  "record": {
    "id": 1,
    "refs": { "doc_ids": [901] }
  }
}
```

Note: If workorder tables don’t yet exist, these payloads serve as the contract for a thin implementation.

### GET filtering examples

- List WorkOrders filtered by status and project fields (projection):

```http
GET /wcapi/work-orders/?status=planned&fields=id,work_no,status
```

- List WorkOrderLines for a specific WorkOrder using the friendly key; mapped to `parent_ref_id` internally:

```http
GET /wcapi/workorder-lines/?workorder_id=123&fields=id,parent_id,status
```

- Strict mode to reject unknown filters (returns 400 with fail envelope):

```http
GET /wcapi/workorder-lines/?unknown=1&strict=1
```

## Implementation phases

Phase 1 (no schema risk):

- Add registry entries (model registry) for workorder and workorder_line as JSON-first models using the standard envelope shapes.
- Expose via universal wcapi endpoints with search and projection parity.
- Use existing linkage, document and question_answer endpoints for attachments.

Phase 2 (performance/clarity):

- Introduce concrete models and migrations with indexes on (status, item_id), (workorder_id, sequence), and timestamp fields.
- Add validators for state changes, enforce foreign keys, and materialize any derived metrics.

Phase 3 (ops niceties):

- Add convenience endpoints: release, start, hold, complete; bulk issue/return materials; QuestionAnswer gate checks.
- Dashboards: WIP by station, bottlenecks, lead-time stats.

## Inventory Integration

When a WorkOrder is completed, use the `complete_workorder()` function to produce finished goods into inventory:

```python
from apps.transactions.services.flow import complete_workorder, CompleteWorkOrderLine

# Define completed lines
lines = [
    CompleteWorkOrderLine(
        wo_line_id=123,
        qty_completed=50,
        warehouse_code='FG',  # Finished goods warehouse
        unit_cost=25.00,
        lot='LOT-2025-001',
    ),
]

# Complete the workorder and receive finished goods
result = complete_workorder(wo, 'WO-COMP-2025-001', lines)
# Result: {'receipt_id': 456, 'stacks_created': [789], 'deltas_created': 1}
```

**Effects:**
- Creates `Receipt` record for traceability
- Creates `InventoryLayer` for finished goods tracking
- Creates inventory delta: `+quantity_on_hand`, `-quantity_on_wo`

For the high-level dispatcher, you can also use:

```python
from apps.transactions.services.flow import receive_inventory_changes

result = receive_inventory_changes('workorder', wo, 'WO-COMP-001', lines)
```

See [Inventory Deltas](../inventory/inventory_deltas.md#inventory-receiving-functions) for full documentation.

## Minimal DB model sketch (later)

WorkOrder:

- item (FK Item)
- quantity, uom
- status (choices)
- scheduled_start/end, actual_start/end (DateTime)
- refs JSON, metadata JSON, prefs JSON, comments JSON
- dt_created/dt_modified (epoch ms), indexes for common filters

WorkOrderLine:

- workorder (FK WorkOrder)
- sequence (int), process (str), station (str?)
- item (FK Item?), qty_required/issued/scrap (Decimal)
- status (choices)
- refs JSON, metadata JSON, prefs JSON, comments JSON
- dt_created/dt_modified
- unique (workorder, sequence), indexes on (workorder) and (status)

## Open questions

- Material backflush strategy per line vs at header?
- Granularity of QuestionAnswer gates (per operation vs per WO)?
- Partial completions and split/merge WOs?

## Next steps

- If this direction looks good, we can wire Phase 1 quickly (registry + endpoints) and iterate to Phase 2 when usage patterns stabilize.

## Admin quick actions

For fast triage, the Django admin for Work Orders includes bulk status actions:

- Release → sets status to `released`
- Start → sets status to `in_progress`
- Hold → sets status to `hold`
- Complete → sets status to `complete`
- Cancel → sets status to `canceled`

Use these to move multiple work orders through typical states without opening each record.

Work Order Lines admin also includes bulk actions:

- Start → sets `status` to `in_progress`
- Done → sets `status` to `done`
- Skip → sets `status` to `skipped`
- Rework → sets `status` to `rework`

All admin actions route through model save() so invalid transitions are blocked and reported.
