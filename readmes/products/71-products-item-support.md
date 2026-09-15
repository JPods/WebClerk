# Products App — Item Supporting Structures
**Created:** 2026-08-09
**Owner:** Alice (pricing, inventory tasks, margin velocity)

---

## What It Does

The products app is the largest app in WC3 — 19 models, 13 service modules (~80 functions), 7 view modules (~32 API views), and 9 Celery tasks. Everything revolves around Item: pricing cascades through Catalogs, inventory flows through Layers, BOMs define assemblies, Serials track individual units, Variants handle size/color, and XRefs cross-reference to external systems.

Flowchart: `readmes/flowcharts/wc3-products-item-support.dot`
```bash
dot -Tpdf readmes/flowcharts/wc3-products-item-support.dot -o readmes/flowcharts/wc3-products-item-support.pdf
```

---

## Model Map

### Core

| Model | Key Fields | Relationship to Item |
|-------|-----------|---------------------|
| **Item** | sku, name, kind, uom, price{}, cost{}, quantity{}, flags{}, tax_code{}, vendor→OrgBase, manufacturer→OrgBase, margin_velocity, margin_pct, annual_turns | Center of everything |
| **ItemLinkedBase** (abstract) | item→Item, status | Base class for all Item extensions |

### Pricing (3 models)

| Model | Key Fields | What it does |
|-------|-----------|-------------|
| **Catalog** | name, code, currency, dt_effective_start/end, orgbase, customer, manufacturer, rep, priority, applies_to{}, is_universal_pct, margin_floor | Price list definition — scoped by customer, vendor, rep, time range |
| **CatalogLine** | catalog→Catalog, item→Item, unit_base_price, unit_cost, margin_floor, qty_discount_tiers{} | Individual item pricing within a catalog — quantity break tiers |
| **OrgItem** | item→Item, orgbase→OrgBase, catalog→Catalog, availability, inventory_frequency, data{}, metrics{} | Per-vendor/customer item data — their SKU, their price, their availability |

**Price resolution stack** (first match wins):
1. OrgItem price for this contact
2. CatalogLine matching contact/catalog/quantity
3. Contact price_level percentage
4. Item.price.base (fallback)

### Inventory (8 models)

| Model | Key Fields | What it does |
|-------|-----------|-------------|
| **Warehouse** | name, code, site_code, location{}, count{}, priority | Physical storage location |
| **InventoryLayer** | item→Item, warehouse→Warehouse, source{}, quantity{}, cost{}, lot, serial_numbers{}, source_doc_type/id, is_locked | Individual receipt lot — FIFO/LIFO costing, lock protection |
| **InventoryMovement** | warehouse→Warehouse, layer→Layer, movement_type, qty, dt_recorded, reference{} | Audit trail of every quantity change |
| **PendingInventoryAdjustment** | layer→Layer, adjustment_type, qty_adjustment, reason, dt_pending | Staged quantity changes — drained every 30s by Celery |
| **InventoryReservation** | item→Item, warehouse→Warehouse, layer→Layer, qty, state, dt_expires, context{} | Soft holds on inventory — pending→committed→released |
| **InventoryCheck** | orgbase, catalog, user, dt_performed, status | Physical count header |
| **InventoryCheckLine** | check→Check, orgitem→OrgItem, planned_qty, counted_qty, variance_qty | Physical count detail — variance drives adjustments |
| **InventoryMetricsSnapshot** | metrics{} | Point-in-time inventory health snapshot |

**Inventory flow:**
```
Receive → InventoryLayer (FIFO/LIFO stack)
    → PendingInventoryAdjustment (staged, 30s drain)
    → InventoryMovement (audit trail)
    → InventoryReservation (soft hold for orders)
    → InventoryCheck → variance → adjustment
```

### Bill of Materials (1 model)

| Model | Key Fields | What it does |
|-------|-----------|-------------|
| **BillOfMaterial** | parent_item→Item, child_item→Item, quantity, scrap_factor, yield_pct, sequence, revision, is_alternate, is_optional, cost_snapshot, dt_effective_from/to | Assembly tree — supports revisions, alternates, scrap, yield, cost rollup |

**BOM services:** expand_tree, propagate_cost_up, consume_bom, find_top_level_assemblies, calc_net_build_qty

### Serial Tracking (2 models)

| Model | Key Fields | What it does |
|-------|-----------|-------------|
| **Serial** | item→Item, serial_ida, model_ida, status, warranty{}, site{}, layer→Layer, qr_code | Individual serialized unit — full lifecycle |
| **SerialLog** | serial→Serial, action, dt, config{} | Audit trail per serial — receive, issue, return, status changes |

**Serial lifecycle:** receive → issue_to_sale → return_from_sale (or) change_status
**Warranty tracking:** warranty{} JSONField with start/end dates, terms

### Variants (1 model)

| Model | Key Fields | What it does |
|-------|-----------|-------------|
| **Variant** | item→Item (1:1), parent_item→Item, canonical_key, attrs{}, set_uuid, variant_uuid | Size/color/config variations — parent→children with shared set_uuid |

### Cross-Reference (1 model)

| Model | Key Fields | What it does |
|-------|-----------|-------------|
| **ItemXRef** | item→Item, source, source_id, external_sku, external_uuid, cost{}, is_preferred | External system SKU mapping — vendor catalogs, marketplace listings |

### Specification (1 model)

| Model | Key Fields | What it does |
|-------|-----------|-------------|
| **Specification** | item→Item, name, unit, details{}, docs{}, applies_to{} | Technical specifications — structured attribute sets |

### Service (1 model)

| Model | Key Fields | What it does |
|-------|-----------|-------------|
| **Service** | item→Item, category, display, billing{}, process{}, travel{}, default_duration_minutes | Service items — labor, consulting, travel with billing rules |

### Usage (1 model)

| Model | Key Fields | What it does |
|-------|-----------|-------------|
| **ItemUsage** | item→Item, year, month, metrics{} | Monthly usage metrics — feeds demand forecasting |

### Delivery (2 models)

| Model | Key Fields | What it does |
|-------|-----------|-------------|
| **DeliveryVisit** | orgbase, customer, catalog, dt_scheduled/arrived/completed, status | Delivery route stop |
| **DeliveryLine** | visit→Visit, orgitem→OrgItem, planned_qty, actual_qty, status | Delivery detail — planned vs. actual |

---

## Service Modules — Complete Registry

| Module | Functions | What it covers |
|--------|----------|---------------|
| **price_resolver.py** | resolve_price, _check_org_item, _check_catalogs, _catalog_applies_to_contact, _find_matching_catalog_line, _apply_catalog_line, _check_contact_price_level, _build_result, _create_margin_approval | First-match-wins pricing cascade |
| **pricing.py** | resolve_price_level, resolve_unit_price, get_price_for_line, get_price_matrix, apply_line_pricing | Line-level pricing for transactions |
| **bom_services.py** | list_bom_lines, create/update/delete_bom_line, recalc_parent_cost, expand_tree, propagate_cost_up, consume_bom, find_top_level_assemblies, calc_net_build_qty | Full BOM lifecycle + cost rollup |
| **inventory_services.py** | create_layer, consume_fifo/lifo, recalc_average_cost, split_layer, transfer_layer, get_count_sheet, record_count, classify_abc, compute_margin_velocity, tally_site_buckets | Layer operations + costing + ABC classification |
| **inventory_stacks.py** | receive_inventory, consume_inventory, get_item_inventory_summary | High-level receive/consume API |
| **inventory_pending.py** | adjust_item_quantity, apply_pending_for_item, get_pending_for_item | Pending adjustment queue |
| **inventory_adjustment_processor.py** | process_pending_inventory, process_pending_for_stack | Celery drain processor (30s adaptive) |
| **inventory_availability.py** | get_item_availability, get_item_availability_by_warehouse | Availability calculations |
| **inventory_reservations.py** | create/commit/release_reservation, reserve/commit/release_for_order, availability_for_layer/item, release_expired | Soft hold management |
| **inventory_metrics.py** | summarize_inventory_metrics, snapshot_inventory_metrics | Health metrics + snapshots |
| **serial_lifecycle.py** | create_serial_on_receive, assign_serial_on_ship, return_serial, get_serial_history, find_serials_by_customer | Serial lifecycle transitions |
| **serial_services.py** | receive, issue_to_sale, return_from_sale, reference_existing, change_status, list_by_item, search_by_*, get_history, warranty_due/expired | Full serial CRUD + warranty |
| **suggest_purchase.py** | get_preferred_vendor, get_items_below_reorder, suggest_purchase_orders, create_draft_purchase | Purchase suggestion engine |
| **map_enforcement.py** | check_map_violation, check_order_map_violations, get_map_violations_report | Minimum Advertised Price enforcement |
| **xref_lookup.py** | lookup_by_external_sku, lookup_by_code, find_item_by_any_identifier | External SKU resolution |
| **purchasing_dashboard.py** | compute_purchasing_dashboard, purchasing_dashboard_to_dict | Purchasing analytics |
| **sales_dashboard.py** | compute_dashboard, dashboard_to_dict | Sales analytics |

---

## Missing Service Functions

### Not Built

| Gap | What's needed | Why it matters | Priority |
|-----|-------------|---------------|----------|
| **UOM Conversion** | Service to convert between units (kg↔lb, CS↔EA, etc.) with stored conversion factors | Alice's conversion pipeline normalizes UOM but WC3 has no runtime conversion for mixed-UOM orders or inventory | High — blocks multi-UOM purchasing |
| **Reorder Point Calculation** | Service to compute optimal reorder point per item/warehouse using demand history + safety stock | `suggest_purchase.py` has `get_items_below_reorder()` but no calculation of what the reorder point should be — it reads a static value | Medium — manual reorder points work but don't adapt |
| **Lot Tracking Model** | Dedicated model for lot numbers with expiry dates, quantity, full traceability | InventoryLayer has a `lot` field (CharField) but no structured lot lifecycle — no expiry alerting, no lot-level holds, no lot trace | Medium — serialized items are covered, lot items are not |

### Stubbed / Phase 5

| Gap | Current state | What's needed |
|-----|-------------|-------------|
| **Multi-Currency Conversion** | `exchange_rate` field stored on InventoryLayer on receipt | No conversion logic — all valuation assumes base currency (USD). Phase 5: conversion service, exchange rate feed, multi-currency costing |
| **Tax Jurisdiction Params** | `tax_code.jurisdiction_params` stub in Item model | Localized product-type handling (food exempt, clothing exempt by state, digital goods) — currently a pass-through |

### Service Functions That Should Exist But Don't

| Function | Module it belongs in | What it would do |
|----------|---------------------|-----------------|
| `convert_uom(qty, from_uom, to_uom, item_id=None)` | New: `uom_services.py` | Convert quantity between UOM using item-specific or global conversion factors |
| `get_uom_factor(from_uom, to_uom, item_id=None)` | New: `uom_services.py` | Look up conversion factor — item-specific overrides global |
| `calculate_reorder_point(item_id, warehouse_id)` | `suggest_purchase.py` | Compute reorder point from ItemUsage demand history + lead time + safety stock |
| `calculate_safety_stock(item_id, warehouse_id)` | `suggest_purchase.py` | Safety stock from demand variability + lead time variability |
| `create_lot(item_id, lot_number, quantity, expiry_date)` | New: `lot_services.py` | Create structured lot record with expiry tracking |
| `consume_lot(lot_id, quantity)` | New: `lot_services.py` | Consume from specific lot — FEFO (First Expiry First Out) |
| `alert_expiring_lots(days_ahead=30)` | New: `lot_services.py` | Celery task: find lots expiring within N days, create Actions |
| `convert_currency(amount, from_curr, to_curr, dt=None)` | New: `currency_services.py` | Convert using stored or fetched exchange rates |
| `refresh_exchange_rates()` | New: `currency_services.py` | Celery task: pull rates from external API, store in Setting |
| `resolve_tax_jurisdiction(item, ship_to_address)` | New: `tax_services.py` | Determine applicable tax rules by product type + jurisdiction |

---

## Celery Tasks

| Task | Schedule | What it does |
|------|----------|-------------|
| `process_pending_inventory_adaptive_task` | Every 30s | Drain pending inventory adjustments — adaptive delay based on workload |
| `expire_inventory_reservations_task` | Beat | Release expired soft holds |
| `check_stale_inventory_records` | Beat | Alert on pending records stuck > 5 minutes |
| Alice: `health_scoring_task` | Daily 2:30 AM | Score item health across all models |
| Alice: `margin_tracking_task` | Weekly Mon 5:00 AM | Track margin trends per item/category |
| Alice: `velocity_task` | Weekly Mon 5:30 AM | Margin × turns ÷ carry cost per item |

---

## View Modules

| Module | Views | Endpoints |
|--------|-------|-----------|
| **bom_views.py** | List, Detail, RecalcCost, ExpandTree, Consume, WhereUsed, PropagateCost | `/wcapi/bom/` |
| **inventory_adjustment_views.py** | Adjust, History, Layers, BOMAdjust | `/wcapi/inventory/adjust/` |
| **inventory_views.py** | Availability, ReservationCreate, ReservationAction, Metrics, Prometheus | `/wcapi/inventory/` |
| **item_inventory_views.py** | BulkItemInventory | `/wcapi/item-inventory/` |
| **item_variants.py** | ItemVariants | `/wcapi/item-variants/` |
| **serial_views.py** | ListByItem, Receive, Issue, Return, Reference, History, Search, Warranty, StatusChange | `/wcapi/serial/` |

---

## Key Architecture Patterns

### ItemLinkedBase
Abstract base class providing `item→Item` FK and `status` field. Used by: InventoryLayer, ItemXRef, OrgItem, Serial, Service, Specification, ItemUsage. Ensures consistent Item relationship across all extensions.

### JSONField Envelopes
Item uses JSONField extensively:
- `price{}` — base, msrp, retail, wholesale, currency
- `cost{}` — standard, avg, last, landed
- `quantity{}` — on_hand, allocated, available, on_order, on_po, on_wo
- `flags{}` — back_order_allowed, discountable, serialized, taxable
- `tax_code{}` — code, category, jurisdiction_params (stub)
- `catalog{}` — category tree, tags

### Pending Adjustment Queue
All inventory changes go through PendingInventoryAdjustment → Celery drains every 30s → InventoryLayer updated → InventoryMovement audit trail created. This decouples transaction speed from inventory processing.

### Price Resolution Cascade
First-match-wins through: OrgItem → CatalogLine (quantity breaks) → contact price_level → Item.price.base. Margin floor enforcement creates approval Actions when price drops below margin_floor.

---

## Files

| Path | What it is |
|------|-----------|
| `apps/products/models/` | All 19 model definitions |
| `apps/products/services/` | All 13 service modules |
| `apps/products/views/` | All 7 view modules |
| `apps/products/tasks.py` | Celery tasks (inventory drain, reservations, stale alerts) |
| `apps/products/admin.py` | Django admin registration |
| `readmes/flowcharts/wc3-products-item-support.dot` | Visual model map |

## Related

| Readme | What it covers |
|--------|---------------|
| `readmes/flowcharts/wc3-inventory-buckets.dot` | Inventory bucket flow (on_hand, on_so, on_po, on_wo → available) |
| `readmes/flowcharts/wc3-inventory-costing.dot` | Layer-based costing (FIFO/LIFO/weighted average) |
| `readmes/flowcharts/wc3-serial-tracking.dot` | Serial lifecycle (receive → reserve → ship → return) |
| `readmes/flowcharts/wc3-price-cascade.dot` | Price resolution cascade |
| `readmes/flowcharts/wc3-bom.dot` | BOM tree: expand, build, cost rollup, where-used |
| `readmes/flowcharts/wc3-forecast-purchasing.dot` | Demand signals → forecast → PO → receive |
| `readmes/70-data-conversion-pipeline.md` | How item data enters WC3 (conversion → bundle → sync) |
| `readmes/69-celery-architecture.md` | Full Celery task registry including inventory tasks |
