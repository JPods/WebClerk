# Org Items (OrgItem)


<!-- TOC START -->

## Table of Contents

- [Org Items (OrgItem)](#org-items-orgitem)
  - [Purpose / When to Use](#purpose-when-to-use)
  - [Model Summary](#model-summary)
    - [Fields](#fields)
    - [Indexes & Constraints](#indexes-constraints)
    - [Access Patterns](#access-patterns)
- [All items for an org](#all-items-for-an-org)
- [Check if org carries an item (any catalog)](#check-if-org-carries-an-item-any-catalog)
- [All orgs carrying an item (any catalog)](#all-orgs-carrying-an-item-any-catalog)
- [Due for inventory check (helper queryset method)](#due-for-inventory-check-helper-queryset-method)
    - [Permissions / Settings Integration](#permissions-settings-integration)
  - [Migration History](#migration-history)
  - [Future Enhancements (Potential)](#future-enhancements-potential)
  - [Conventions Applied](#conventions-applied)
  - [Removal / Deprecation Notes](#removal-deprecation-notes)
  - [Quick Reference Snippets](#quick-reference-snippets)
- [Create association (no catalog)](#create-association-no-catalog)
- [Bulk ensure](#bulk-ensure)
- [Access thresholds snapshot](#access-thresholds-snapshot)

<!-- TOC END -->

Canonical association between an organization (`OrgBase`) and an `Item` indicating the item is listed / carried / offered by that org (customer, vendor, channel, etc.). Neutral naming avoids implying ownership or stock while enabling assortment / catalog style use cases.

## Purpose / When to Use

- Determine which items an org can purchase, sell, or display
- Drive price list, merchandising, availability, or channel enablement logic
- Basis for derived analytics (assortment breadth, adoption, gaps)

## Model Summary

| Aspect | Value |
|--------|-------|
| Django class | `apps.products.models.org_item.OrgItem` |
| Table registry key | `org_items` |
| Endpoint slug (planned) | `org-items` |
| Uniqueness | (`item`, `org`, `catalog`) via `uniq_item_org_catalog` (catalog nullable; allows multiple catalogs) |
| Related name on OrgBase | `org_items` |
| Security field | `security_level` (integer tier) |

### Fields

| Field | Type | Notes |
|-------|------|-------|
| id | PK | BigAutoField |
| item | FK -> `products.Item` | Inherited from `ItemLinkedBase` |
| org | FK -> `orgs.OrgBase` | `related_name="org_items"` |
| catalog | FK -> `products.Catalog` (nullable) | Scopes association to catalog context |
| description | Char(255) | Freeform assortment / merchandising note |
| security_level | Integer (indexed) | Optional tier / ACL discriminator |
| availability_state | Char(20 choices) | enabled / paused / retired |
| quantity_minimum | Decimal(14,4) nullable | Min threshold (mirrors JSON) |
| quantity_maximum | Decimal(14,4) nullable | Max threshold (mirrors JSON) |
| inventory_frequency | Char(30 choices) | daily / weekly / monthly / 30d |
| dt_last_checked | BigInt nullable (indexed) | Epoch ms of last verification |
| dt_next_check | BigInt nullable (indexed) | Epoch ms next verification due |
| data | JSONB | Operational envelope (thresholds, scheduling) |
| metadata envelope fields | From `BaseModel` chain via `ItemLinkedBase` | Standard refs / prefs / metadata / comments |

### Indexes & Constraints

- Unique: (`item`, `org`, `catalog`) name: `uniq_item_org_catalog`
- Indexes: (`org`, `item`), (`org`, `availability_state`), (`org`, `security_level`), (`catalog`), (`dt_last_checked`), (`dt_next_check`)

### Access Patterns

Common query shapes:

```python
# All items for an org
items = OrgItem.objects.filter(org=some_org).select_related("item")

# Check if org carries an item (any catalog)
exists = OrgItem.objects.filter(org=org, item=item).exists()

# All orgs carrying an item (any catalog)
carriers = OrgItem.objects.filter(item=item).select_related("org")

# Due for inventory check (helper queryset method)
due = OrgItem.objects.due_for_check()
```

### Permissions / Settings Integration

Because `org_items` is in `TABLE_REGISTRY`, any `Setting` rows that target this table name will be validated. Add granular field-level permissions (view/edit) using the standard Settings matrix if needed.

## Migration History

- Introduced originally as `ItemCarried` in `products 0001_initial`.
- Renamed to `OrgItem` via migration `0002_rename_itemcarried_orgitem`.
- Related name changed from `items_carried` to `org_items` (no-op migration `0003_alter_orgitem_related_name`).
- Expanded with catalog FK, enumerated availability / inventory frequency, scheduling timestamps, promoted thresholds & next-check field, and updated uniqueness prior to consolidated migration.

## Future Enhancements (Potential)

| Area | Idea |
|------|------|
| Denormalized metrics | Cache latest sales / movement stats for faster filtering |
| Channel attributes | Add JSON keys or separate model if large |
| Partial indexes | Filtered index on dt_next_check for due items |
| Soft uniqueness | Add is_active to allow historical rows |
| Auditing | Signals / ChangeLog entries for state transitions |

## Conventions Applied

- Plural table registry key / endpoint (`org_items` / `org-items`)
- Neutral naming ("OrgItem") describing relationship not action
- Operational JSON plus promoted scalar fields for indexed querying

## Removal / Deprecation Notes

Legacy module `items_carried.py` previously raised an `ImportError` to surface stale imports. It was fully removed (cleanup) after migration squash and OrgItem adoption (2025-09-05). If you see references to `items_carried` in old branches, replace with `OrgItem` imports from `apps.products.models.org_item`.

## Quick Reference Snippets

```python
from apps.products.models import OrgItem

# Create association (no catalog)
OrgItem.objects.get_or_create(org=o, item=i, catalog=None, defaults={"description": "Listed 2025-09-04"})

# Bulk ensure
missing = desired_item_ids - set(OrgItem.objects.filter(org=o).values_list("item_id", flat=True))
OrgItem.objects.bulk_create([OrgItem(org=o, item_id=iid) for iid in missing])

# Access thresholds snapshot
org_item.get_thresholds()
```

---
Add improvements or clarifications here as usage patterns evolve.
