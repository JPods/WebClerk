# Universal API Conventions

> **Reading order**: [← 05-model-registry](05-model-registry.md) | [07-react-integration →](07-react-integration.md)

---

This document captures the conventions used by the Universal API endpoints (e.g., `/wcapi/get`, `/wcapi/save`) for model naming, related data, and forward link hydration.

## 1) Singular model_name (strict)

- Always pass a singular `model_name` (e.g., `order`, `invoice`, `purchase`, `proposal`, `item`, `phone`, `email`, `org`, `customer`, `vendor`).
- Plural table keys are rejected with HTTP 400 and a hint to the proper singular.
- Transitional aliases are accepted and normalized (e.g., `address` -> `location`, `org_item` -> `item`).

## 2) Related data buckets (plural)

- The response contains a `data.related` object keyed by canonical plural buckets, because values are arrays.
- Canonical buckets include (non-exhaustive):
  - Lines: `order_lines`, `invoice_lines`, `purchase_lines`, `proposal_line` (historical singular name kept; may alias to `proposal_lines` later).
  - Communications & orgs: `phones`, `emails`, `addresses`, `customers`, `vendors`.

## 3) Forward link hydration via refs.links

- The server reads `record.refs.links` and will hydrate specified buckets in `related`.
- Input is forgiving: singular keys and aliases are accepted and normalized to canonical buckets before hydration.

Accepted aliases (examples):

- Common singular to plural:
  - `address` -> `addresses`
  - `phone` -> `phones`
  - `email` -> `emails`
  - `item` -> `items`
  - `contact` -> `contacts`
  - `vendor` -> `vendors`
- Line buckets:
  - `order_line` -> `order_lines`
  - `invoice_line` -> `invoice_lines`
  - `purchase_line` -> `purchase_lines`
  - `proposal_lin` -> `proposal_line`

## 4) Header-specific refs.links shapes

- Sales Order / Invoice / Proposal:
  - Include: `items[]`, `contacts[]`, `customers[]`, `address[]`, `phone[]`, `email[]`
  - Lines:
    - Sales Order: `order_lines[]`
    - Invoice: `invoice_line[]` (normalized to `related.invoice_lines`)
    - Proposal: `proposal_lin[]` (normalized to `related.proposal_line`)
- Purchase Order:
  - Include: `item[]` (singular), `contact[]`, `vendor[]`, `address[]`, `phone[]`, `email[]`
  - Lines: `purchase_line[]` (normalized to `related.purchase_lines`)

## 5) Examples

- GET detail

  Request:

  ```json
  { "model_name": "invoice", "id": 123 }
  ```

  Response (excerpt):

  ```json
    {
      "success": true,
      "data": {
        "record": { "refs": { "links": { "items": [1,2], "invoice_line": [10,11] } } },
        "related": {
          "invoice_lines": [ {"id": 10, ...}, {"id": 11, ...} ],
          "phones": [ ... ],
          "emails": [ ... ],
          "addresses": [ ... ],
          "customers": [ ... ]
        }
      }
    }
  ```

## 6) Rationale

- Singular `model_name`: clarity and predictability in requests.
- Plural related buckets: values are arrays; keeps naming symmetrical.
- Flexible refs.links inputs: easier authoring; backend normalizes to stable buckets.

If you need additional aliases or buckets, open a PR or note here and we’ll extend the normalization list.
