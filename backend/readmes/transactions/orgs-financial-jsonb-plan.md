## Plan: Implement Per-Model `financial` JSONB for Orgs

### Overview
This revised plan keeps **all financial data stored directly inside the existing `.financial` JSONB blob of each OrgBase record**, with no additional database objects and no cross-record lookups.

The goal is to **avoid retrieving multiple records** and to **keep financial data tightly coupled to each organization instance**, while still allowing per‑org‑type structure.

### New convention
```
org.financial = {
  // all data lives here, per org record
  "credit": {...},
  "balances": {...},
  "aging": {...},
  "sales": {...},
  "vendor_specific": {...},
  "rep_specific": {...},
  ...
}
```

Each org_type simply uses **its own subset** of this blob.

This keeps:
* **One JSONB field per org**
* **Zero extra queries**
* Flexible evolution of keys
* Complete backward compatibility

---

## 1. Backend Changes (Django)

### 1.1 Keep `OrgBase.financial` exactly as it is
Only requirement: define **per‑org‑type subkeys inside the existing blob**, e.g.:
```
financial.customer = { ... }
financial.vendor = { ... }
```
But all stored in **one JSON document**.

### 1.2 Optional migration
Only if you want to group existing keys.
Otherwise, **no migration is required**.

### 1.3 Update Pydantic schemas
* Create per-model financial schemas.
* Update `OrgSnapshot` and `OrgSnapshotPatch` to support the new structure.

### 1.4 Update API save/load logic
* Ensure `org.financial[org_type]` maps correctly.
* Maintain backward compatibility for HTTP clients still sending root-level `financial`.

---

## 2. Frontend Changes (React)

### 2.1 Update TypeScript org model types
Introduce:

```
interface OrgFinancial {
  common?: OrgFinancialCommon;
  customer?: OrgFinancialCustomer;
  vendor?: OrgFinancialVendor;
  rep?: OrgFinancialRep;
  employee?: OrgFinancialEmployee;
  manufacturer?: OrgFinancialManufacturer;
}
```

### 2.2 Update OrgDetail to pass `.financial` unchanged
OrgFinancialsPanel decides which keys to show based on `org_type`.

### 2.3 Update OrgFinancialsPanel
* Continue using a single `financial` blob.
* Each tab reads only the keys relevant to its org type.
* No structural changes needed.

### 2.4 Update list/grid components (OrgList, OrgEntityList)
Only required if they display summary financial info.

---

## 3. Migration Steps (Minimal or None)

### 3.1 Database migration
* No schema change — only JSON transformation.
* Create Django migration:
  * Load existing `financial` dict.
  * Wrap into `{ "common": old_financial }`.

### 3.2 API compatibility
* During rollout, accept both formats.
* Log/telemetry events for clients still submitting root-level financial.

---

## 4. Implementation Order
1. Backend: optionally refine schemas for `.financial`
2. Update orgApi TS types
3. Update OrgFinancialsPanel to read keys by org_type
4. Update OrgDetail only as needed
5. No DB migration required unless grouping existing keys

---

## 5. Mermaid Sequence Diagram
```
graph TD
  A[API Loads Org] --> B[Backend loads financial JSON]
  B --> C[Transform to per-model financial structure]
  C --> D[React OrgDetail receives nested structure]
  D --> E[OrgFinancialsPanel renders correct tab]
```

---

## 6. Done
This plan can now be used for implementation.
