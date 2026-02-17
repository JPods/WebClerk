# Model Rename Guard

> Completed February 2026. This document records the canonical model names
> adopted during development and the automated check that prevents regression.

---

## Renamed Models

| Legacy Name | Canonical Name | Scope |
|---|---|---|
| `SalesOrder` / `sales_order` | `Order` / `order` | model class, model_name key, API, registry, readmes |
| `SalesOrderLine` / `sales_order_line` | `OrderLine` / `order_line` | model class, model_name key, API, registry |
| `PurchaseOrder` / `purchase_order` | `Purchase` / `purchase` | model class, model_name key, API, registry, readmes |
| `PurchaseOrderLine` / `purchase_order_line` | `PurchaseLine` / `purchase_line` | model class, model_name key, API, registry |
| `Location` / `location` (comm model) | `Address` / `address` | model class, model_name key, API, registry, readmes, SDK types |

### What was NOT renamed

These legitimate uses of "location" are **not** part of the rename and should
be preserved as-is:

- **`Warehouse.location`** — JSONField for physical aisle/shelf/bin position
- **`InventoryLayer.location_id`** — FK to warehouse storage location
- **`Serial.site`** — site/location snapshot for physical tracking
- **`GlAccount` comment** — "Sub-account/Location" is accounting terminology
- **`OpenApiParameter.QUERY` `location=`** — DRF parameter location (query vs body)
- **`Address.db_table = 'locations'`** — kept to avoid DB migration; the Django table stays `locations`
- **`Address.metadata.display.full_location`** — computed display field for formatted address string
- **`_compute_display_location()`** — method computing the display label

## Guard Script

**`tools/check_renamed_models.sh`** scans both projects for reintroduction of
legacy model-name keys in code and readmes. Run it before merging a branch:

```bash
# From the webClerk3 root
bash tools/check_renamed_models.sh
```

Exit code **0** = clean, **1** = violations found.

### What it checks

| Pattern | Context | Why it's banned |
|---|---|---|
| `'sales_order'` / `"sales_order"` | Python/TS model keys | Use `order` |
| `'purchase_order'` / `"purchase_order"` | Python/TS model keys | Use `purchase` |
| `SalesOrder` (class ref) | Python/TS imports | Class is now `Order` |
| `PurchaseOrder` (class ref) | Python/TS imports | Class is now `Purchase` |
| `'location'` as model key | Python model_name dicts | Use `address` |
| `Location = Address` | Python alias | Removed — import `Address` directly |
| `location_verification` | Connection type string | Now `address_verification` |
| `validate_location_osm` | Task function name | Now `validate_address_osm` |
| `verify_location_via_connection` | Service function name | Now `verify_address_via_connection` |

### Allowed exceptions (not flagged)

- `db_table = 'locations'` — intentional DB table name
- `Warehouse.location` field — physical location, not the model
- `OpenApiParameter.QUERY location=` — DRF parameter position
- `full_location` / `_compute_display_location` — display helpers
- `location.state` in templates / routing — React Router
- Migration files — historical Django migrations
- `__pycache__`, `node_modules`, `.git`, `venv` directories
- Archive session notes (`_archive/session-notes/`) — historical record

## CI Integration

To add this as a GitHub Actions check:

```yaml
# .github/workflows/rename-guard.yml
name: Model Rename Guard
on: [pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: bash tools/check_renamed_models.sh
```

## History

- **Feb 2026** — `SalesOrder` → `Order`, `PurchaseOrder` → `Purchase`,
  `Location` → `Address` completed across React2025 and webClerk3.
  All backward-compat aliases removed. Guard script created.
