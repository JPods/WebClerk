# Warehouse Model Overview

<!-- TOC START -->

## Table of Contents

- [Warehouse Model Overview](#warehouse-model-overview)
  - [Table of Contents](#table-of-contents)
  - [Core Concepts](#core-concepts)
  - [`count` JSON Schema](#count-json-schema)
  - [Typical Usage](#typical-usage)
  - [Non‑Goals](#non-goals)
  - [Indexing & Query Patterns](#indexing--query-patterns)
  - [Data Quality Guidelines](#data-quality-guidelines)
  - [Extensibility Considerations](#extensibility-considerations)
  - [Migration / Legacy Notes](#migration--legacy-notes)
  - [Quick Example](#quick-example)
  - [Summary](#summary)

<!-- TOC END -->

Intent: Provide a fast, human‑navigable registry of places where inventory is (or can be) stored so people can quickly answer: "Where is this stuff?" and "What locations do we have?". It is **not** an inventory ledger; it is a directory of storage locations plus a lightweight latest count snapshot.

## Core Concepts

- `Warehouse` represents a physical or logical storage location (building, cage, trailer, virtual buffer, 3PL site).
- Each record carries a globally unique `code` (human short identifier) and an optional `site_code` grouping multiple locations under a site / campus / fulfillment center.
- The `location` JSON may hold structured address / geo / contact metadata (keep it sparse; only what helps people find it physically).
- The `count` JSON captures a **single most recent physical count snapshot** with fine‑grained sub‑location hints (`aisle`, `column`, `shelf`, `bin`). It is deliberately not historic—history should live in a dedicated inventory events or movements table in the future.

## `count` JSON Schema

```jsonc
{
  "value": 0,                   // last physically counted quantity (non‑negative)
  "aisle": "",                 // optional granular locator
  "column": "",                // vertical or planar subdivision
  "shelf": "",                 // shelf identifier
  "bin": "",                   // bin / tote / slot identifier
  "counted_by": "",            // human label (username/display)
  "counted_by_id": null,        // internal user id if known
  "dt_counted": 0,              // UTC ms timestamp when captured
  "deviation": 0                // variance vs system expectation (signed)
}
```

This snapshot lets an operator see the last verified on‑hand quantity and where exactly it was verified, without loading heavier movement histories.

## Typical Usage

- Directory / selection lists when assigning inbound receipts or picking tasks.
- Displaying last known verified quantity & time in UI detail panes.
- Rapid reconciliation workflows: call `warehouse.update_count(value, user, deviation, aisle=..., bin=...)` then save.

## Non-Goals

- Not a multi‑period audit trail (avoid appending history here).
- Not a replacement for item‑level location assignments if you later model racks/slots as separate entities.
- Not enforcing complex geo hierarchies—keep free‑form, rely on simple indexes.

## Indexing & Query Patterns

Indexes:

- `(site_code, is_active)` for listing current active locations per site.
- `(is_active, priority)` to quickly pull prioritized active locations.

Common queries:

- Filter active: `Warehouse.objects.filter(is_active=True)`
- Site scoped: `filter(site_code=..., is_active=True)`
- Ordered by operational importance: `order_by('-priority')` (string priority taxonomy: e.g. critical > high > normal > low).

## Data Quality Guidelines

- Keep `code` short (<= 40 chars), stable, and human legible (avoid internal numeric ids alone).
- Normalize `priority` to a constrained vocabulary (document any custom values separately).
- Trim location sub‑fields (`aisle`, `bin`, etc.) to <= 80 chars (enforced in validation) and avoid embedding multi‑value composites; prefer multiple warehouses if materially different.

## Extensibility Considerations

If you later require:

- Historical counts: introduce a `WarehouseCount` event table (warehouse FK, item FK if item‑scoped, value, dt_counted, user, deviation).
- Finer granularity (rack / slot): model a `Location` hierarchy and link `Warehouse` as a top node.
- Capacity planning: add fields (capacity_units, capacity_type) rather than overloading `count`.

## Migration / Legacy Notes

Legacy schemas stored many discrete physical locator columns directly on per‑item warehouse tables. We collapsed these into a single JSON snapshot to simplify early evolution. The current model purposely keeps the surface minimal while giving operators enough metadata to find products.

## Quick Example

```python
wh = Warehouse.objects.create(code="A1", site_code="MAIN", name="Main Floor A1")
wh.update_count(125, user=request.user, deviation=+2, aisle="A", shelf="3", bin="A1-03-07").save()
```

Item linkage lives in `refs.links.items` (list of item ids) rather than inside the count snapshot.

Resulting `count`:

```json
{
  "value": 125,
  "aisle": "A",
  "column": "",
  "shelf": "3",
  "bin": "A1-03-07",
  "counted_by": "jdoe",
  "counted_by_id": 42,
  "dt_counted": 1725400000000,
  "deviation": 2
}
```

## Summary

`Warehouse` is a searchable directory of storage locations plus a lightweight last count snapshot to help humans quickly locate and trust where inventory resides right now. Keep it lean; push history and heavy analytics into specialized tables when needed.
