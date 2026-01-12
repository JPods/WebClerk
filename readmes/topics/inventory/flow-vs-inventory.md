# Flow vs Inventory Domain

<!-- TOC START -->

## Table of Contents

- [Flow vs Inventory Domain](#flow-vs-inventory-domain)
  - [Table of Contents](#table-of-contents)
  - [TL;DR](#tldr)
  - [When To Add a Field](#when-to-add-a-field)
  - [Cross-Referencing](#cross-referencing)
  - [Variance → Adjustment Workflow (Future)](#variance-adjustment-workflow-future)
  - [Avoiding Leakage Between Domains](#avoiding-leakage-between-domains)
  - [Extension Points](#extension-points)
  - [Flow Action Endpoints](#flow-action-endpoints)
  - [Naming Conventions](#naming-conventions)
  - [Roadmap Ideas](#roadmap-ideas)
  - [Quick Decision Guide](#quick-decision-guide)

<!-- TOC END -->

This guide clarifies the boundary between **Flow** (delivery / execution) models and **Inventory** (audit / valuation) models so features land in the right place without duplication.

## TL;DR

| Aspect | Flow (DeliveryVisit / DeliveryLine) | Inventory (InventoryCheck / InventoryCheckLine) |
|--------|-------------------------------------|-------------------------------------------------|
| Primary Question | "What movement is happening?" | "What do we actually have?" |
| Intent | Execute logistic stop (deliver, pickup, confirm) | Capture a point‑in‑time stock snapshot |
| Lifecycle Focus | Route scheduling & status transitions | Counting workflow & variance capture |
| Core Status Path | planned → en_route → arrived → closed/canceled | planned → in_progress → completed/canceled |
| Quantity Fields | planned_qty / loaded_qty / delivered_qty | prior_qty / counted_qty / variance_qty |
| Source of Truth For | Operational events & fulfillment KPIs | Accuracy, shrink, reconciliation KPIs |
| JSON Envelope (`data`) | Device, geo, pricing, adjustments, media refs | Method, device, zone scope, confidence, anomalies |
| Typical KPIs | OTIF %, stop duration, partial/skip rates | Variance %, shrink $, cycle coverage %, accuracy % |
| Write Frequency | Real-time during route execution | Burst at count windows (periodic / ad hoc) |
| Adjustment Side Effects | May trigger inventory *movements* (issue/receipt) | May create *adjustments* (after approval) |
| Concurrency | One active visit per vehicle/route segment | Many overlapping checks (zones) acceptable |
| Failure Patterns | Missed stop, partial delivery, route delay | Large variance, missing lines, stale prior snapshot |

## When To Add a Field

Add to Flow if it describes how a *stop* or *line movement* occurred (who scanned, truck temperature, signature, dynamic pricing snapshot).

Add to Inventory if it describes *count methodology*, *confidence*, *scope*, or *result interpretation* (RFID vs manual, double-pass verification, zone identifier, recount count).

## Cross-Referencing

It is valid for a DeliveryVisit and an InventoryCheck to share a time window and even a physical location. We do **not** embed an InventoryCheck inside a DeliveryVisit to keep responsibilities clean:

- The visit might finish even if the check is still in progress (e.g., counting extended).
- A count can occur independently (off-route / ad hoc cycle count).

Linking strategy (if/when needed):

- Add a nullable FK `inventory_check` on `DeliveryVisit` **or** a small reference block in `InventoryCheck.data` (e.g., `{ "related_visit_id": 123 }`) once correlation is required by reporting.
- Prefer soft linking (IDs in JSON) until a hard relational need emerges, to avoid migration churn.

<!-- markdownlint-disable-next-line MD033 -->
<a id="variance-adjustment-workflow-future"></a>

## Variance → Adjustment Workflow (Future)

1. InventoryCheck completes.
2. Lines with |variance_qty| over threshold or flagged (`auto_flag=True`) enter a review queue.
3. Approved lines generate *inventory adjustments* (distinct model) applied through the same inventory layer / pending adjustment engine for consistency.
4. Movement ledger consolidates adjustments & delivery movements for an audit trail.

## Avoiding Leakage Between Domains

Anti-patterns:

- Adding delivered_qty to an InventoryCheckLine (belongs in Flow).
- Adding variance_qty to a DeliveryLine (variance is audit-only context).
- Overloading Flow `data` with extended counting methodology (belongs in Inventory).

## Extension Points

| Need | Place It | Rationale |
|------|----------|-----------|
| Reverse logistics / pickups | Flow (new model e.g. ReturnVisitLine) | Still an execution event (physical movement). |
| Continuous cycle sampling engine | Inventory services module | Drives creation of InventoryCheck records. |
| Real-time stock confirmation at delivery | Flow line `data` snapshot | Moment captured during movement, not a full audit. |
| AI anomaly scoring | InventoryCheckLine.auto_flag / data | Enhances variance triage. |
| Route optimization metrics | DeliveryVisit.data or analytic table | Execution-side concern. |

## Flow Action Endpoints

The following write-once actions convert headers along the sales flow and are part of the Flow domain:

- POST `/transactions/proposals/<pk>/convert-to-sales-order/`
  - Body: `{ "confirm": true }` (optional)
  - 201 Response: `{ "sales_order_id": <int>, "order_no": "SO-..." }`

- POST `/transactions/sales-orders/<pk>/convert-to-invoice/`
  - Body: `{ "confirm": true }` (optional)
  - 201 Response: `{ "invoice_id": <int>, "invoice_ida": "<stringified id>" }`

Notes

- These actions copy lines forward and preserve core JSON envelopes (`item`, `quantity`, `price`, `cost`, `tax`, etc.).
- Permissions are governed by `view_edit` rules keyed by singular `model_name`.
- Idempotency is not guaranteed; only call once per header or implement guardrails upstream.

## Naming Conventions

- Keep `Delivery*` prefixes for flow visit/line classes until/unless a broader rename (`FlowVisit`) is adopted (migration required then).
- Keep `InventoryCheck*` for audit events to maintain grep-ability and clarity.

## Roadmap Ideas

- Movement Ledger: unify DeliveryLine finalizations + approved adjustments into a chronological, queryable stream.
- Count Coverage Metrics: % of active items counted in last N days by segment (zone, category, velocity tier).
- Hybrid Stop Mode: Attach a lightweight micro-count subset directly to a DeliveryVisit (for high-risk SKUs) while deferring full audits to InventoryCheck.
- Recount Orchestration: Automatic creation of follow-up InventoryChecks when variance beyond tolerance detected.

## Quick Decision Guide

If the feature answers:

- "How did product move?" → Flow
- "What do we truly have?" → Inventory
- "Why is there a mismatch?" → Inventory (variance / reconciliation layer)
- "Should we adjust stock now?" → Inventory (post-approval), executed through inventory adjustment mechanics

---
Keep this doc updated as new execution or audit concepts are introduced. Small clarifications welcome; large scope changes should reference a design note or ADR.
