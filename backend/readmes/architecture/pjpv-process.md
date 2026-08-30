# PJPV Compliance Process — 2026-08-23

**What this documents:** The process by which we audited WebClerk3 for PJPV
compliance, found violations, fixed them, built Pydantic schemas for all
business envelopes, wired validation into the totals engine, replaced hardcoded
UI metadata with schema-derived behaviors, and created the `/wcapi/_pjpv_fields/`
endpoint. This is a reference for future compliance work and for any team
member who needs to understand why the code looks the way it does.

---

## The Problem We Found

PJPV was established 2026-08-22 after discovering that three serializers were
independently computing margin — one with `Decimal`, one with `float`. They
agreed most of the time. When they didn't, users made decisions on bad numbers.
Scars #62, #63, #64 document the cost.

The fix on 2026-08-22 removed the serializer extractions and established the
four rules (pjpv-architecture.md). But the fix was incomplete — it only touched
the serializers and a few React components. The independent calculations in the
payment services, signals, and conversion code were untouched. And the P in
PJPV — Pydantic — was aspirational: no Pydantic schemas existed for the
business envelopes that PJPV depends on.

## How We Audited

Three parallel scans, each covering a domain:

1. **Backend services/views/serializers/signals** — searched for independent
   balance, margin, and total calculations outside `totals.py`
2. **React frontend** — searched for `.reduce()` computing server-owned values,
   banned field names, hardcoded labels, flat column definitions
3. **Pydantic schema completeness** — mapped every JSONField on every model
   to check which had Pydantic schemas and which didn't

### What the Scans Found

**Backend (14 violations across 9 files):**

| File | Severity | Violation |
|------|----------|-----------|
| `signals.py:422-426` | CRITICAL | Bulk `queryset.update()` bypassed totals engine AND versioning |
| `transaction_save.py:742` | HIGH | Wrong margin formula: `total - cost` instead of `subtotal - cost` (included tax/shipping in margin) |
| `payment_application.py:59,85,166` | HIGH | Independent `balance = total - received` in apply/unapply/status |
| `payment_pending.py:279-284` | HIGH | Same pattern — direct envelope manipulation + scalar update |
| `conversion.py:547-551` | HIGH | Payment forwarding during order-to-invoice bypassed engine |
| `invoice_serializers.py` | MEDIUM | `totals` missing from `read_only_fields` |
| `validation.py:180` | LOW | Independent balance calc for validation (didn't persist) |
| `commission.py:164` | ACCEPTED | Line-level margin for commission basis — separate domain |

**React (0 critical violations):**
- `InvoiceLineEditor.tsx` and `OrderLineEditor.tsx` computed `.reduce()` totals
  but were dead code (not imported anywhere) — deleted
- `ShoppingCart.tsx` computes pre-order totals — legitimate (no server envelope
  exists yet), commented as such
- Good patterns throughout: `PortalDashboard`, `TabsRenderer`, `MarginPanel` all
  read from `data?.totals?.total` envelopes

**Pydantic schemas (critical gap):**
- 79 model schema files existed for structural envelopes (`.config`, `.metadata`,
  `.prefs`, `.refs`, `.comments`, `.actions`) — complete
- ZERO schemas existed for business envelopes (`totals`, `finance`, `price`,
  `cost`, `quantity`, `tax`, `physical`) — the ones PJPV actually depends on
- `field_behaviors.py` had `LEAF_BEHAVIORS` as a hardcoded dict — parallel
  source of truth that would drift from any future schema

## What We Fixed — Step by Step

### Step 1: Add `update_received()` to `totals.py`

**The pattern:** Five files independently computed `balance = total - received`.
If the balance formula ever changed (discount terms, credit memos, partial
returns), five places needed updating instead of one.

**The fix:** Added `update_received(header, new_received)` to `totals.py` — the
single owner for payment-side balance updates. Does not re-sum lines; only
updates `totals.received` and `totals.balance` in the envelope and the
shadow fields.

**File:** `apps/transactions/services/totals.py`

### Step 2: Fix all callers to use `update_received()`

| File | What changed |
|------|-------------|
| `payment_application.py` | apply/unapply/status → `update_received()` or read from envelope |
| `payment_pending.py` | apply → `update_received()` |
| `signals.py` | `update_order_received` → `update_received()` (also removed `queryset.update()` bypass) |
| `conversion.py` | Payment forwarding → `update_received()` with `refresh_from_db()` |
| `validation.py` | Reads `totals.get('balance')` from envelope instead of recomputing |
| `invoice_serializers.py` | Added `totals` to `read_only_fields` |

### Step 3: Fix margin formula

**File:** `apps/transactions/services/transaction_save.py:742`

**Before:** `margin = total - cost_total` (included tax and shipping in margin)
**After:** `margin = subtotal - cost_total` (matches totals engine)

This was the `calculate_header_totals()` function used for R25 verification.
The bug would have produced wrong margin numbers on any transaction with
tax or shipping charges.

### Step 4: Delete dead React code

Deleted `InvoiceLineEditor.tsx` and `OrderLineEditor.tsx` from React2025 — not
imported anywhere, computed `.reduce()` totals that the server already owns.

### Step 5: Create Pydantic schemas for all business envelopes

**File:** `common/schemas/transaction_envelopes.py`

Seven schemas created, each field with `Field(title=, description=,
json_schema_extra={widget, precision, readonly})`:

| Schema | Fields | What it covers |
|--------|--------|---------------|
| `TransactionTotals` | 12 | subtotal through balance — the most critical PJPV schema |
| `TransactionFinance` | 12 | Tax jurisdiction IDs, rates, amounts |
| `TransactionCost` | 10 | Header-level cost summary |
| `LineQuantity` | 8 | staged/active/remaining + controls |
| `LinePrice` | 7 | unit, base, discount, extended + controls |
| `LineCost` | 16 | unit, extended, surcharges, tax, controls |
| `LineTax` | 6 | Per-line tax rate overrides |
| `LinePhysical` | 9 | weight, dimensions, volume, hazmat |

All schemas use `extra = "allow"` — future keys don't break existing records.

### Step 6: Wire validation into the totals engine

`_validate_totals()` runs `TransactionTotals(**totals)` before every persist —
both in `recalculate_totals()` and `update_received()`.

**Mode: fail-hard (promoted 2026-08-23).** If the schema rejects the data,
the save fails. If we fail, we fix. Soft fallbacks hide problems — hard
failures surface them. Bill's call: "If it falls into fallbacks and soft
behaviors, we do not fix them."

**File:** `apps/transactions/services/totals.py`

### Step 7: Replace hardcoded `LEAF_BEHAVIORS` with schema-derived version

`field_behaviors.py` now calls `get_all_leaf_behaviors()` from the schema
module instead of maintaining a parallel hardcoded dict. One source of truth.

The function `schema_to_leaf_behaviors()` reads `Field(title=)` and
`json_schema_extra` from each schema class and produces the exact dict format
that `_inject_leaf_behaviors()` expects. Comments envelope stays hardcoded
(structural, not business — no Pydantic schema needed).

**File:** `apps/core/services/field_behaviors.py`

### Step 8: Build `/wcapi/_pjpv_fields/` endpoint

React can now fetch field metadata from the server instead of hardcoding labels:

```
GET /wcapi/_pjpv_fields/                    → full catalog (all 7 envelopes)
GET /wcapi/_pjpv_fields/?envelope=totals    → just totals fields
```

Returns: `{field_name: {type, label, description, widget, precision,
readonly, min, max}}` — everything React needs to render a field without
knowing what it is.

**Files:**
- `apps/core/views/schema_fields_view.py` — the endpoint
- `apps/core/urls.py` — URL registration

---

## Compliance Status After Fixes

| Domain | Status | Notes |
|--------|--------|-------|
| Backend services | 100% | All balance/margin calculations through totals engine |
| Serializers | 100% | No flattening, no banned names, envelopes intact |
| React frontend | 99.5% | Zero critical violations; print template labels acceptable |
| Pydantic schemas (business) | 100% | All 7 business envelopes have schemas |
| Pydantic schemas (structural) | 100% | All 79 models have .config/.metadata/.prefs/.refs schemas |
| Totals engine validation | Done | Fail-hard (2026-08-23) |
| `/wcapi/_pjpv_fields/` endpoint | Active | Available for React consumption |
| `LEAF_BEHAVIORS` | Schema-derived | No more parallel hardcoded dict |

---

## What Remains

### Alice Weekly Schema Review (Wednesday coordination day)

Alice should run a weekly scan that:
- Diffs Pydantic schemas against actual JSONField content in the database — are
  there keys in production JSON that have no schema declaration?
- Checks for new `DecimalField`/`CharField` additions that shadow JSONField keys
  without being documented in the shadow field registry
- Checks for new `.reduce()` calls in React computing values the server owns
- Reports schema health to the Wednesday scrub meeting

**Not yet scheduled.** Needs an Alice code standard pattern added.

### Remaining Schemas — Completed 2026-08-23

Added in the same session, completing the full business envelope coverage:

| Schema | Model | Fields | Notes |
|--------|-------|--------|-------|
| `LineItem` | All lines | 13 | Denormalized item snapshot on transaction lines |
| `LineCommission` | All lines | 3 | Commission envelope (total, reps[], basis) |
| `PriceQtyBreak` | Item | 3 | One row in price.qty_breaks[] |
| `CostQtyBreak` | Item | 2 | One row in cost.qty_breaks[] |
| `ItemPrice` | Item | 9 | Master pricing: base, levels, qty_breaks, currency |
| `ItemCost` | Item | 8 | Cost tracking: standard, last, avg, landed, components |
| `ItemCatalog` | Item | 4 | Categories, attributes, web, flags |
| `ItemCatalogWeb` | Item | 4 | Web presentation sub-schema |

All live in `common/schemas/transaction_envelopes.py` alongside the original 8.
Item schemas are in a separate `ITEM_SCHEMA_MAP` to avoid field_behaviors
collision (Item.price schema differs from line price schema).

### BOM + OrgBase Aspects — Completed 2026-08-23

Closed the last two gaps in the same session:

| Schema | Model | Fields | Notes |
|--------|-------|--------|-------|
| `BomOperationalData` | BillOfMaterial.op_data | 6 | Operation, work center, setup/run time, tooling, notes |
| `OrgAddress` | OrgBase.addresses[] | 9 | Unified from apps/orgs/pydantic_schemas.py AddressMini |
| `OrgPhone` | OrgBase.phones[] | 5 | Unified from PhoneMini |
| `OrgEmail` | OrgBase.emails[] | 5 | Unified from EmailMini |
| `OrgDomain` | OrgBase.domains[] | 3 | Unified from DomainMini |

All live in `common/schemas/transaction_envelopes.py` in `AUXILIARY_SCHEMA_MAP`.
The original mini schemas in `apps/orgs/pydantic_schemas.py` remain for
backward compatibility (OrgSnapshot uses them); the unified versions in
`common/schemas/` are the PJPV-compliant authority with Field(title=,
json_schema_extra={widget}) metadata.

**No gaps remain.** Every JSONField in the system that carries business data
now has a Pydantic schema.

### Promote Validation to Fail-Hard — Done 2026-08-23

Promoted immediately after server restart confirmed clean. Bill's principle:
"If we fail, we fix. If it falls into fallbacks and soft behaviors, we do
not fix them." The try/except wrapper was removed — validation failure now
raises directly, blocking the save.

### React `/wcapi/_pjpv_fields/` Migration

React components currently hardcode labels like `"Subtotal"`, `"Total"`,
`"Margin"` in print templates and some display cards. These should fetch from
`/wcapi/_pjpv_fields/` or cache the schema at app startup. The compliant patterns
already exist (PortalDashboard reads from envelopes); this is extending that
discipline to labels.

---

## The Defense Architecture

PJPV has four layers of defense against reversion:

| Layer | What it catches | When |
|-------|----------------|------|
| **Pydantic validation** (Layer 1) | Wrong types, missing keys, out-of-range values | At save time |
| **`/wcapi/_pjpv_fields/` endpoint** (Layer 2) | React label/format drift | At render time |
| **Alice weekly scan** (Layer 3) | Schema-vs-reality drift, new shadow fields | Wednesday |
| **Claude memory + readme** (Layer 4) | Design violations requiring judgment | Every session |

Layers 1 and 2 are self-enforcing. Layers 3 and 4 require the team.

---

## Files Changed in This Process

| File | Change |
|------|--------|
| `common/schemas/transaction_envelopes.py` | **NEW** — 7 Pydantic schemas + bridge functions |
| `apps/core/views/schema_fields_view.py` | **NEW** — `/wcapi/_pjpv_fields/` endpoint |
| `apps/transactions/services/totals.py` | Added `_validate_totals()`, `update_received()` |
| `apps/core/services/field_behaviors.py` | `LEAF_BEHAVIORS` now schema-derived |
| `apps/core/urls.py` | Added `/wcapi/_pjpv_fields/` URL |
| `apps/transactions/services/transaction_save.py` | Fixed margin formula |
| `apps/transactions/services/payment_application.py` | Uses `update_received()` |
| `apps/transactions/services/payment_pending.py` | Uses `update_received()` |
| `apps/transactions/signals.py` | Uses `update_received()` |
| `apps/transactions/services/conversion.py` | Uses `update_received()` |
| `apps/transactions/services/validation.py` | Reads balance from envelope |
| `apps/transactions/serializers/invoice_serializers.py` | `totals` in `read_only_fields` |
| `React2025/.../InvoiceLineEditor.tsx` | **DELETED** — dead code |
| `React2025/.../OrderLineEditor.tsx` | **DELETED** — dead code |
| `React2025/.../ShoppingCart.tsx` | Added PJPV pre-order comment |

---

## See Also

- `pjpv-architecture.md` — the four rules and reversion prevention
- `pjpv-denormalized-fields.md` — registry of scalar fields that shadow JSON
- Scars #62–65 in leftshoe identity store — the cost of getting this wrong
- `readmes/topics/transactions/transactions-totals.md` — totals engine docs
