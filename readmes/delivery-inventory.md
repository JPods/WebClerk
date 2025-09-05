# Delivery & Inventory Verification Models


<!-- TOC START -->

## Table of Contents

- [Delivery & Inventory Verification Models](#delivery-inventory-verification-models)
  - [Purpose](#purpose)
  - [Model Overview](#model-overview)
  - [Delivery Flow](#delivery-flow)
  - [Inventory Check Logic](#inventory-check-logic)
  - [Metrics Strategy](#metrics-strategy)
  - [Key Helper Methods](#key-helper-methods)
  - [Constraints / Integrity](#constraints-integrity)
  - [Scheduling / Due Checks](#scheduling-due-checks)
  - [Future Enhancements](#future-enhancements)
  - [Example Snippets](#example-snippets)
- [Update plan vs actual after delivery](#update-plan-vs-actual-after-delivery)
- [Record catalog sync completion](#record-catalog-sync-completion)
- [Build basic replenishment DeliveryVisit (pseudo code)](#build-basic-replenishment-deliveryvisit-pseudo-code)

<!-- TOC END -->

Unified documentation for the just-in-time operational models introduced alongside `OrgItem` & `Catalog` metric expansions.

## Purpose

Enable a restaurant/vendor (or broader vendor → customer) workflow:

1. Plan a delivery route (DeliveryVisit + DeliveryLines).
2. Perform on-site inventory verification (InventoryCheck + Lines).
3. Adjust planned delivery based on real counts (variance pruning / substitutions).
4. Capture plan vs actual metrics at both `OrgItem` and `Catalog` levels for feedback loops.


## Model Overview

| Model | Key Fields | Description |
|-------|------------|-------------|
| `DeliveryVisit` | vendor_org, customer_org, catalog?, dt_scheduled, status, data, metrics (future) | A single trip / stop context for potential delivery + check |
| `DeliveryLine` | visit, org_item, planned_qty, loaded_qty, delivered_qty, status, skipped_reason, data | Item-level planned vs executed delivery record |
| `InventoryCheck` | org, catalog?, performed_by, dt_performed, status, data | A point-in-time on-hand quantity verification session |
| `InventoryCheckLine` | inventory_check, org_item, counted_qty, prior_qty, variance_qty, auto_flag, data | Count result for a specific org_item within a check |
| `OrgItem.metrics` | plan_last_qty, actual_last_qty, variance_last_qty, rolling_daily_usage, etc. | Per relationship performance feedback (consumption & accuracy) |
| `Catalog.metrics` | item_count, plan_value_total, fill_rate_pct, dt_last_sync, etc. | Aggregated plan vs actual & sync KPIs at catalog scope |

## Delivery Flow

1. Pre-Plan: Build `DeliveryVisit` with `status=planned` and associate candidate `DeliveryLine` rows (planned_qty derived via threshold logic or replenishment algorithm).
2. Load: Transition line status to `loaded` as items are placed on truck (optionally capture loaded_qty if partial).
3. Arrival: Mark visit `status=arrived`; optional `InventoryCheck` begins for the customer org (may reuse catalog context).
4. Inventory Check: Lines created for targeted `OrgItem` rows. `counted_qty` gathered; `variance_qty` auto-computed.
5. Reconcile: Drop/adjust `DeliveryLine` rows where on-hand already meets/exceeds thresholds; convert remaining to `delivered` or `partial`.
6. Metrics Update: Update `OrgItem.metrics` via `update_plan_actual(planned_qty, delivered_qty)` and roll-up aggregated value deltas into `Catalog.metrics` (external service / task).
7. Close: Set visit `status=closed`; finalize `InventoryCheck` status `completed`.

## Inventory Check Logic

Auto-Flagging concept (`InventoryCheckLine.auto_flag`): set by business logic (future service) when:

- counted_qty < quantity_minimum
- counted_qty > quantity_maximum (oversupply)
- Large variance vs prior_qty beyond tolerance.


`variance_qty` is automatically computed on save when both prior & counted present.

## Metrics Strategy

Per-row vs Aggregated:

- `OrgItem.metrics` stores only the latest plan vs actual context (small surface, fast writes).
- `Catalog.metrics` stores catalog-level KPIs. Rolling 30d usage, margin %, fill rate, etc., can be recomputed by scheduled tasks.


Why JSON:

- Evolvable without schema churn.
- Allows phased introduction of derived metrics.
- Minimal overhead; values promoted only if they become query filters.


Promotion Guidance:

- If queries like "catalogs with fill_rate_pct < 85" become frequent, add a promoted decimal field + index later.


## Key Helper Methods

| Object | Helper | Purpose |
|--------|--------|---------|
| OrgItem | `update_plan_actual(plan, actual)` | Update per-row plan vs actual metrics & accuracy |
| Catalog | `touch_pricing()` | Stamp pricing change time |
| Catalog | `record_sync()` | Stamp last successful integration sync |
| Catalog | `update_plan_actual_value(plan, actual)` | Update value variance metrics |

## Constraints / Integrity

| Area | Enforcement |
|------|-------------|
| OrgItem uniqueness | (item, org, catalog) via `uniq_item_org_catalog` |
| OrgItem thresholds | CheckConstraints ensure non-negative + ordering |
| Catalog code | Unique per vendor_org (`uniq_catalog_code_vendor`) |
| Catalog temporal range | `effective_dt_end >= effective_dt_start` or null end |
| DeliveryVisit / Catalog alignment | `clean()` validates vendor/customer match |
| InventoryCheckLine uniqueness | (inventory_check, org_item) |
| DeliveryLine uniqueness | (visit, org_item) |

## Scheduling / Due Checks

`OrgItem.dt_next_check` auto-populated based on `inventory_frequency` and `dt_last_checked` when present. Frequency mapping:

- daily → +86,400,000 ms
- weekly → +7 days
- monthly / 30d → +30 days


Query Due Items:

```python
due_items = OrgItem.objects.due_for_check()
```

## Future Enhancements

| Category | Idea |
|----------|------|
| Historical metrics | Append time-series table for plan vs actual history |
| Forecasting | Derive rolling_daily_usage & days_of_supply asynchronously |
| Fill rate | Compute line-level fill_rate_pct boosters for Catalog.metrics |
| Partial indexes | Filtered index on dt_next_check < now for large datasets |
| Event sourcing | Emit domain events (delivery.completed, inventory.check.completed) for downstream consumers |
| Access control | Per-visit driver permissions scoping to customer_org + vendor_org linkage |

## Example Snippets

```python
# Update plan vs actual after delivery
org_item.update_plan_actual(planned=25, actual=22)
org_item.save(update_fields=["metrics", "dt_modified"])

# Record catalog sync completion
catalog.record_sync()
catalog.save(update_fields=["metrics", "dt_modified"])

# Build basic replenishment DeliveryVisit (pseudo code)
visit = DeliveryVisit.objects.create(vendor_org=vendor, customer_org=restaurant, dt_scheduled=now_ms)
low_stock_items = OrgItem.objects.for_org(restaurant).filter(quantity_minimum__isnull=False)
for oi in low_stock_items:
    DeliveryLine.objects.get_or_create(visit=visit, org_item=oi, defaults={"planned_qty": oi.quantity_minimum})
```

---
Refine this document as workflows stabilize and new KPIs are introduced.
