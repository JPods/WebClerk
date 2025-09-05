# Service Billing Guide


<!-- TOC START -->

## Table of Contents

- [Service Billing Guide](#service-billing-guide)
  - [1. Purpose](#1-purpose)
  - [2. JSON Schema (v1)](#2-json-schema-v1)
  - [3. Core Operations](#3-core-operations)
  - [4. Validation](#4-validation)
  - [5. Concurrency (`row_version`)](#5-concurrency-rowversion)
  - [6. Auditing](#6-auditing)
  - [7. Travel Pricing](#7-travel-pricing)
  - [8. Rounding](#8-rounding)
  - [9. Min / Max Charge](#9-min-max-charge)
  - [10. Schema Evolution](#10-schema-evolution)
  - [11. Management Command](#11-management-command)
  - [12. Testing](#12-testing)
  - [13. Pitfalls](#13-pitfalls)
  - [14. Extending](#14-extending)
  - [15. Legacy / Migration Notes](#15-legacy-migration-notes)
  - [16. Example](#16-example)
  - [17. Glossary](#17-glossary)
  - [18. Feature Checklist](#18-feature-checklist)
  - [19. Future Ideas](#19-future-ideas)
  - [20. Support](#20-support)
  - [21. Changelog](#21-changelog)
  - [22. Diagrams](#22-diagrams)
    - [22.1 Charge Computation Flow](#221-charge-computation-flow)
    - [22.2 Data / Relationship Overview](#222-data-relationship-overview)
    - [22.3 Concurrency Save Sequence](#223-concurrency-save-sequence)
    - [22.4 Scan Command Lifecycle](#224-scan-command-lifecycle)

<!-- TOC END -->

This guide explains how service billing works: schema, operations, validation, auditing, concurrency, and extension patterns.

---

## 1. Purpose

`Service.billing` is a versioned JSON envelope enabling:

* Tiered labor pricing
* Travel surcharges
* Rounding policies
* Min / max charge enforcement
* Change auditing
* Forward compatibility via `schema_version` + `extensions`

---

## 2. JSON Schema (v1)

See `readmes/service_schemas.md` for the authoritative list. Simplified example:

```json
{
  "currency": "USD",
  "tiers": [
    {"unit": "hour", "rate": 150.0, "cost": 90.0, "min_minutes": 30, "dt_effective": 1736123456000}
  ],
  "travel": {"per_mile": 2.5, "per_hour": 0.0, "included_miles": 10, "dt_updated": 1736123000000},
  "rounding": {"strategy": "HALF_UP", "places": 2},
  "min_charge": null,
  "max_charge": null,
  "schema_version": 1,
  "version": 1,
  "extensions": {}
}
```

Key rules:

* Tiers strictly increase by `dt_effective`.
* Allowed units: `hour`, `minute`, `day`, `flat`.
* `min_minutes` floors billable time for that tier.
* Monetary numbers normalized internally to consistent precision.

---

## 3. Core Operations

Add / update rate:

```python
svc.add_rate(rate=175, unit="hour", min_minutes=60, dt_effective=epoch_ms)
svc.save()
```

Get current rate:

```python
current = svc.current_rate("hour")
```

Compute charge:

```python
charge = svc.compute_charge(minutes=90, miles=40, unit="hour")
```

Charge algorithm steps:

1. Pick latest tier for unit.
2. Enforce `min_minutes`.
3. Base = time * rate (convert to hours if needed).
4. Travel surcharge = (max(0, miles - included_miles) * per_mile).
5. Apply rounding strategy.
6. Enforce min/max charge.

Edge cases: no tier → 0.0; negative inputs → `ValueError`.

---

## 4. Validation

On `clean()` / `save()`:

* Currency: 3 alpha chars.
* Chronological, unique `dt_effective`.
* Allowed units only.
* Non-negative numeric fields.
* Unique process step names (case-insensitive).
* Concurrency: `row_version` match required.

---

## 5. Concurrency (`row_version`)

* Starts at 0 on create.
* Incremented on each update save.
* Stale instance save → `ValidationError`.

---

## 6. Auditing

`billing_audit` keeps last 100 entries:

```json
{"dt": 1736123456000, "summary": "Added tier unit=hour rate=175", "row_version": 5}
```

---

## 7. Travel Pricing

Per-mile surcharge implemented; `per_hour` reserved. Extend via `travel` or `extensions` when adding new distance/time metrics.

---

## 8. Rounding

Current: `HALF_UP` (fallback uses Python `round`). Configure decimal places via `rounding.places` (default 2).

---

## 9. Min / Max Charge

`min_charge` floors; `max_charge` caps after rounding. Use for contract enforcement and small engagement viability.

---

## 10. Schema Evolution

Upgrade flow: implement transforms in `ensure_billing_schema()` and bump `schema_version`. Non-breaking additions go under `extensions`.

---

## 11. Management Command

```bash
python manage.py scan_service_billing --limit 200 --fix
```

Scans, normalizes, and optionally fixes invalid billing envelopes.

---

## 12. Testing

See `tests/test_service_billing.py` covering: rate add, rounding, travel, caps, currency validation, duplicate tier rejection, process uniqueness, concurrency.

---

## 13. Pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| Charge = 0 | No tier for unit | Add tier matching unit |
| Concurrency error | Stale `row_version` | Re-fetch & retry |
| Duplicate tier error | Same `dt_effective` | Adjust timestamp |
| Negative field error | Bad input | Sanitize before insert |
| Unexpected rounding | Strategy / places mismatch | Verify `rounding` keys |

---

## 14. Extending

Prefer `billing.extensions` for additive keys; update normalization & validation; add tests; bump `schema_version` only for breaking changes.

---

## 15. Legacy / Migration Notes

Legacy booleans moved to `Item.flags`. Plain text tax codes wrapped into JSON before column type change (see migration `0002_drop_legacy_cost_price_and_flags_json`). Follow same pattern for future primitive → JSON upgrades.

---

## 16. Example

```python
from apps.products.models.service import Service
from apps.products.models.item import Item

item = Item.objects.create(name="Install Labor", kind=Item.KIND_SERVICE)
svc = Service(item=item, description="Standard install")
svc.add_rate(rate=125, unit="hour", min_minutes=60, dt_effective=1736123000000)
svc.billing["travel"]["per_mile"] = 2.0
svc.billing["travel"]["included_miles"] = 15
svc.save()

charge = svc.compute_charge(minutes=90, miles=40)
print(charge)
```

---

## 17. Glossary

* Tier: Pricing record keyed by `dt_effective`.
* Effective Timestamp: Millisecond epoch controlling activation order.
* Min Billable Minutes: Floor for engagement billing.
* Rounding Strategy: Rule for precision of final charge.
* Travel Surcharge: Distance-based addition beyond included miles.

---

## 18. Feature Checklist

1. Update schema docs.
2. Add schema keys / extensions.
3. Normalize & validate.
4. Add upgrade path if breaking.
5. Add tests.
6. Update README.

---

## 19. Future Ideas

* Usage / volume brackets.
* Regional multipliers.
* Drive time billing (`per_hour`).
* Materialized pricing snapshot.
* Multi-currency conversion layer.

---

## 20. Support

Owner: Products Domain Team
Escalation: Create issue label `service-billing` with `Service.id` & billing JSON.

---

## 21. Changelog

* v1 Initial schema (tiers, travel, rounding, min/max, audit, concurrency)

---

End of document.

---

## 22. Diagrams

### 22.1 Charge Computation Flow

```mermaid
flowchart TD
  A[Input Request\nminutes, miles, unit] --> B[Normalize / validate inputs]
  B --> C[Select current tier for unit]
  C -->|No tier| R[Return 0.0]
  C -->|Tier found| D[Enforce min_minutes]
  D --> E[Convert time -> billable quantity]\n
  E --> F[Base = qty * rate]
  F --> G[Travel surcharge = max(0, miles - included) * per_mile]
  G --> H[Total = Base + Travel]
  H --> I[Apply rounding strategy]
  I --> J[Apply min_charge floor]
  J --> K[Apply max_charge cap]
  K --> L[Return final charge]
  R:::terminal
  L:::terminal

  classDef terminal fill=#0b7285,stroke=#09414e,color=#fff;
```

### 22.2 Data / Relationship Overview

```mermaid
classDiagram
  class Item {
    +BigInt id
    +CharField kind
    +JSON price
    +JSON cost
    +JSON flags
  }
  class Service {
    +BigInt id
    +FK item_id
    +JSON billing
    +JSON process
    +JSON travel
    +JSON actions
    +JSON billing_audit
    +int row_version
    +method add_rate()
    +method current_rate()
    +method compute_charge()
  }
  Item <|-- Service : extends
```

### 22.3 Concurrency Save Sequence

```mermaid
sequenceDiagram
  participant C1 as Client A
  participant C2 as Client B
  participant DB as Database

  C1->>DB: SELECT Service (row_version=3)
  C2->>DB: SELECT Service (row_version=3)
  C1->>DB: UPDATE Service (row_version=3->4)
  DB-->>C1: OK (row_version now 4)
  C2->>DB: UPDATE Service (row_version=3)
  DB-->>C2: ValidationError (stale row_version)
  C2->>DB: SELECT Service (row_version=4)
  C2->>DB: UPDATE Service (row_version=4->5)
  DB-->>C2: OK
```

### 22.4 Scan Command Lifecycle

```mermaid
flowchart LR
  S[scan_service_billing] --> Q[Query batch of Service ids]
  Q --> N[Normalize billing envelope]
  N --> V[Validate structure & semantics]
  V -->|Errors| E[Report / optionally fix]
  V -->|OK| A[Accumulate stats]
  E --> B{--fix?}
  B -->|Yes| F[Write corrected JSON]
  B -->|No| C[Leave unchanged]
  F --> Q
  C --> Q
  A --> Q
  Q --> X{More rows?}
  X -->|Yes| Q
  X -->|No| R[Summary output]
  R:::terminal
```

---
