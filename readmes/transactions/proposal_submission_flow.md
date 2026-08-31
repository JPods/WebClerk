# Proposal Submission Flow

<!-- TOC START -->

## Table of Contents

- [Proposal Submission Flow](#proposal-submission-flow)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Models](#models)
  - [Serializers](#serializers)
  - [Views / Endpoints](#views--endpoints)
  - [Flow Service](#flow-service)
  - [URL Summary](#url-summary)
  - [Typical Client Sequence](#typical-client-sequence)
  - [Field / Permission Considerations](#field--permission-considerations)
  - [Error & Edge Cases](#error--edge-cases)
  - [Extension Points](#extension-points)
  - [Minimal Test Sketch](#minimal-test-sketch)
  - [Data Linkage & Lineage](#data-linkage--lineage)

<!-- TOC END -->

End-to-end flow for a contact/user associated with a customer creating a Proposal with three lines, then converting it to an Order. Includes involved layers (models, serializers, views, services, URLs) and extension points.

## Overview

1. Auth as contact/user with permission.
2. POST header (`/tx/proposals/`).
3. POST three lines (`/tx/proposal-lines/`).
4. (Optional) GET aggregate totals.
5. POST convert to Order.
6. Work with created Order & copied lines.

## Models

- `transactions.models.Proposal` – minimal header (name, dt_created).
- `transactions.models.ProposalLine` – inherits from `BaseLineModel`, FK `parent` to Proposal (db_table `proposal_line`).

`BaseLineModel` supplies pricing, costing, quantity, refs/links JSON, probability (proposal‑specific), etc.

## Serializers

- `ProposalSerializer` – create/update proposal headers.
- `ProposalLineSerializer` – extends base line serializer; requires `parent`.

## Views / Endpoints

- `GET/POST /tx/proposals/` → list/create proposals.
- `GET/PUT/PATCH/DELETE /tx/proposals/{id}/` → detail/update.
- `GET/POST /tx/proposal-lines/?parent_ref_id={id}` → list/create lines for a proposal.
- `GET/PUT/PATCH/DELETE /tx/proposal-lines/{id}/` → line detail.
- `POST /tx/proposals/{id}/convert-to-order/` → conversion action.
- `GET /tx/lines/aggregate/?parent_ref_id={id}&model=proposal-line` → totals.

## Flow Service

`transactions.services.flow.proposal_to_order(proposal)`:

1. Create `Order` (order_no synthesized if not supplied).
2. Load `ProposalLine` rows and iterate.
3. Copy standard line fields via `_copy_common_line_fields` (item, qty, cost/price, refs/links, metadata JSON).
4. Normalize / adjust where schema diverges (qty, pricing).
5. Persist lineage/linkage info for downstream traceability.

## URL Summary

```text
/tx/proposals/
/tx/proposals/<id>/
/tx/proposals/<id>/convert-to-order/
/tx/proposal-lines/
/tx/proposal-lines/<id>/
/tx/lines/aggregate/
```

## Typical Client Sequence

1. Create proposal header:

  POST /tx/proposals/

  ```json
  {
    "name": "Website redesign Q4",
    "status": "draft"
  }
  ```

  → 201 Created { "id": 42, ... }

1. Add three lines (repeat 3x):

  POST /tx/proposal-lines/

  ```json
  {
    "parent": 42,
    "item": { "sku": "SKU-1" },
    "qty": 5,
    "price_each": "100.00",
    "cost_each": "60.00"
  }
  ```

1. (Optional) Fetch lines:

  GET /tx/proposal-lines/?parent_ref_id=42

1. Aggregate totals:

  GET /tx/lines/aggregate/?parent_ref_id=42&model=proposal-line
  → { "proposal-line": { "lines": 3, "price_extended": "300.00", ... } }

1. Convert to order:

  POST /tx/proposals/42/convert-to-sales-order/
  → 201 Created { "order_id": 77, ... }

1. Inspect order & lines.

## Field / Permission Considerations

- Field visibility/editability matrices: `GET /tx/auth/fields/?model=proposal-line`.
- Role-based forms should prefetch these rules.
- Probability field primarily relevant for proposal lines.

## Error & Edge Cases

- Lines before header exists → 400 (FK constraint).
- Unique collisions on line JSON/item require client alteration.
- Conversion of missing proposal → 404; invalid status → consider 409.

## Extension Points

- Status transition validation (draft → submitted → accepted → converted).
- Copy comments/attachments during conversion.
- Batch line create endpoint.
- Pricing/tax service integration pre-aggregate.

## Minimal Test Sketch

```text
1. auth_client posts proposal -> 201
2. create 3 proposal lines -> each 201
3. GET aggregate -> lines == 3
4. POST convert-to-sales-order -> 201 & new id
5. verify new order has 3 lines
```

## Data Linkage & Lineage

- Linkage ID (stored in refs.links) lets downstream documents trace back to original proposal.

---
This guide describes the canonical create → line add → aggregate → convert progression.
