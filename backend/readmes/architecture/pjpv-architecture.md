# PJPV — Pydantic JSON Path Value

**Established:** 2026-08-22
**Status:** Fundamental requirement for all WC3 data behavior

## What PJPV Is

PJPV is the complete data behavior stack — a four-letter architecture that governs
how every value in WebClerk flows from definition to display. Every computed value,
every label, every format rule, every calculation resolves through this chain.

```
Pydantic (schema)  →  JSON (envelope)  →  Path (resolution)  →  Value (display)
```

PJPV is not a library. It is not a pattern you apply sometimes. It is the
fundamental requirement that provides:

| Behavior | What PJPV provides | Where it lives |
|----------|-------------------|----------------|
| **Typing** | Field types: Decimal, int, str, bool, List, nested objects | Pydantic model schemas |
| **Formatting** | Currency, percentage, date rules — display is a field property, not a component property | Pydantic field_info, schema metadata |
| **Labels** | field_info.title, description — the field names itself, not the UI | Pydantic schema, served via /api/schema/ |
| **Values** | JSON envelope is the source of truth — one place, one engine writes it | Server-side totals engine, model save() |
| **Calculations** | All computed values resolve through explicit paths: `totals.margin`, `price.extended` | Path resolution in React, column accessorKey |

## Why PJPV Exists

WebClerk3 replaced 45,091 lines of hand-coded detail pages with ~1,759 lines of
JSON-driven rendering (DynamicDetail, 2026-08-03). This was only possible because
the component doesn't need to know what it's rendering. PJPV tells it everything:
the type, the format, the label, the value, and where the calculation lives.

The alternative — what every other commerce platform does — is components that
know their own fields. An InvoiceDetail knows it has a `total_amount` field,
formats it as currency, labels it "Total", and sometimes computes it locally.
Multiply that by 30+ models and you get 45K lines of repetitive code that
drifts out of sync.

## The Four Rules

### 1. Pydantic is the schema authority

Every model's field behaviors — types, labels, formatting, widget hints, validation
rules — are declared in Pydantic schema code. Not in the database. Not in React
components. Not in Settings (Settings store *layouts*, not *behaviors*).

```python
class InvoiceTotals(BaseModel):
    subtotal: Decimal = Field(title="Subtotal", ge=0)
    tax: Decimal = Field(title="Tax", ge=0)
    total: Decimal = Field(title="Total", ge=0)
    margin: Decimal = Field(title="Margin")
    margin_pc: float = Field(title="Margin %")
    received: Decimal = Field(title="Received", ge=0)
    balance: Decimal = Field(title="Balance")
```

The schema IS the API contract. If a field exists in the schema, it exists in
the envelope. If it doesn't, it doesn't.

### 2. JSON envelopes travel intact

Serializers never flatten, extract, or reshape JSON envelopes. The envelope
goes out the way it was computed. React receives the same structure Pydantic defined.

**Wrong:**
```python
# Serializer extracts from envelope into top-level scalar
def to_representation(self, instance):
    data = super().to_representation(instance)
    data['total_amount'] = instance.sell.get('total', 0)  # WRONG
    data['margin_amount'] = sell_total - cost_total        # WRONG
    return data
```

**Right:**
```python
# Serializer passes envelope as-is
class OrderSerializer(ModelSerializer):
    class Meta:
        fields = [..., 'totals', 'sell', 'cost', ...]
        read_only_fields = ['totals']
```

`total` and `balance` are `@property` methods that read from the `totals` JSONField
envelope. They are not database columns — do not include them in serializer fields.

### 3. Path resolution replaces property access

React components resolve values through dot-path notation, not direct property
access. The path comes from configuration (Settings, column definitions), not
hardcoded in the component.

**Wrong:**
```tsx
// Component knows its own fields
<span>{record.total_amount}</span>
<span>{record.margin_percentage}%</span>
```

**Right:**
```tsx
// Component resolves from envelope via path
<span>{record?.totals?.total}</span>
<span>{record?.totals?.margin_pc}%</span>

// Or via configured column definition (TanStack / DataGrid pattern)
{ header: 'Total', accessorKey: 'totals.total', format: 'currency' }
{ header: 'Margin', accessorKey: 'totals.margin_pc', format: 'percentage' }
```

### 4. One engine computes, everyone else reads

Every computed value is produced by exactly one engine. If two functions compute
the same value, one is wrong — consolidate immediately.

- **Totals engine** (`services/totals.py`) owns `totals.*` — subtotal, tax,
  shipping, total, cost, margin, margin_pc, received, balance
- **Line recalculation** (`recalculate_line`) owns `price.extended`, `cost.extended`
- **Pydantic schemas** own type declarations, labels, formatting

React never computes authoritative totals. It may compute selection-aware
subtotals (partial sums over user-selected lines), but these are clearly labeled
as partial — never confused with the server total.

## What PJPV Replaces

| Before PJPV | After PJPV |
|-------------|-----------|
| Serializers extract `total_amount` from `sell.total` | Serializer passes `totals` envelope intact |
| React computes subtotals from line arrays via `.reduce()` | React reads `totals.subtotal` from server |
| Each component knows its own field names and formats | Component resolves path from schema/config |
| 45K lines of per-model detail pages | 1,759 lines of DynamicDetail |
| Labels hardcoded in JSX | Labels from Pydantic `field_info.title` |
| Format rules scattered across components | Format rules in schema metadata |
| Three serializers computing margin independently (Decimal vs float disagreement) | One totals engine, one computation, one type |

## Selection-Aware Subtotals

The one place local computation is legitimate: when the user selects a subset of
lines and the UI shows a subtotal for only those lines. The server can't know what
the user selected.

Rules for selection-aware subtotals:
- Label them explicitly: "Totals for 3 selected lines" (see `selectionLabel`)
- Never use them where the authoritative total should appear
- When no selection is active, prefer the server envelope total
- The commission fallback pattern: `data?.commission?.total ?? localReduce()`

## Industry Context

Research (2026-08-22) confirmed: every successful open-source commerce project
passes nested JSON intact from API to React.

| Project | Envelope pattern | Totals |
|---------|-----------------|--------|
| **Saleor** | GraphQL fragments resolve `order.total.gross.amount` | Server-computed, nested |
| **Medusa** | `decorateTotals` injects computed totals at retrieval time | Computed and attached |
| **Invoice Ninja** | Line items moved from DB table to JSON array (v4→v5) | Server-computed from JSON |
| **Odoo** | Nested one2many records survive intact | Server-computed |
| **ERPNext** | DocType parent contains child tables as nested arrays | Server-computed |

None of these have Pydantic owning field behaviors end-to-end. The P is what
makes WC3's architecture different — the schema carries type, format, label,
and widget information, not just structure.

## Files Changed (2026-08-22)

| File | Change |
|------|--------|
| `transaction_serializers.py` | Removed `total_amount`/`margin_amount`/`margin_percentage` extraction. Added `totals`/`total`/`balance` to Proposal, Order, Purchase, Invoice serializers. |
| `base_serializers.py` | Commission: removed envelope mutation, now removes `commission` field entirely for non-staff. |
| `TransactionPrint.tsx` | Footer total reads `totals.total` from envelope. |
| `TransactionTabPanel.tsx` | Path arrays reordered: `totals.total` first, removed dead `total_amount`. |
| `invoiceSchema.ts` | Replaced `total_amount`/`paid_amount` with `total`/`totals` envelope. |

## Claude Reversion Prevention — READ THIS

**Every new Claude Code session will try to undo PJPV.** Claude's training data is
full of tutorials that teach serializer flattening, React local computation, and
per-component field knowledge. Without this section, Claude will naturally:

1. Add `to_representation()` that extracts values from JSON envelopes into top-level scalars
2. Use `.reduce()` in React to compute totals the server already computed in `totals.*`
3. Create TypeScript interfaces that duplicate Pydantic schema definitions
4. Add `SerializerMethodField` to flatten nested JSON into top-level fields
5. Put labels, formatting, and type knowledge in React components instead of
   reading from Pydantic schema
6. Create `total_amount`, `margin_amount`, `margin_percentage` or similar
   scalar fields that shadow values already in the `totals` envelope

**These are the EXACT patterns removed on 2026-08-22.** Scars #62, #63, #64
document the cost. Three serializers were independently computing margin —
one with `Decimal`, one with `float`. They agreed most of the time. When they
didn't, users made decisions on bad numbers.

### What Alice and Athena Watch For

Alice's code standards scanner checks for `pjpv-reversion` violations:

| Pattern | What it means | Severity |
|---------|--------------|----------|
| `to_representation` + `.get('total')` in serializer | Extracting from envelope | HIGH |
| `SerializerMethodField` on a model with JSONField | Likely flattening | HIGH |
| New `DecimalField`/`IntegerField` on serializer that shadows envelope key | Scalar duplicate | HIGH |
| `.reduce()` computing sum that exists in `totals.*` | Independent computation | MEDIUM |
| `total_amount`, `margin_amount`, `margin_percentage` in new code | Banned field names | HIGH |
| Labels hardcoded in JSX for fields that exist in Pydantic schema | Scattered behavior | LOW |

### When a Reversion is Detected

1. **FAULT immediately** — don't wait for session end
2. **Reference this readme** — the explanation is here, not in Claude's training data
3. **Show the correct pattern** — read from envelope, don't extract
4. **Check if the totals engine already computes the value** — it almost certainly does

### The Correct Patterns

**Serializer — pass envelope, don't extract:**
```python
# CORRECT
class OrderSerializer(ModelSerializer):
    class Meta:
        fields = [..., 'totals', 'sell', 'cost']
        read_only_fields = ['totals']

# WRONG — this is what Claude will try to write
class OrderSerializer(ModelSerializer):
    total_amount = serializers.DecimalField(read_only=True)  # NO
    margin_amount = serializers.DecimalField(read_only=True)  # NO

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['total_amount'] = instance.sell.get('total', 0)  # NO
        data['margin_amount'] = sell - cost  # NO
        return data
```

**React — read from envelope, don't compute:**
```tsx
// CORRECT — read server-computed value
<span>{formatCurrency(data?.totals?.total)}</span>
<span>{formatCurrency(data?.totals?.margin)}</span>

// CORRECT — configured column
{ accessorKey: 'totals.total', format: 'currency' }

// WRONG — this is what Claude will try to write
const total = lines.reduce((s, l) => s + (l.extended_price || 0), 0);  // NO
const margin = lines.reduce((s, l) => s + (l.line_margin || 0), 0);    // NO
```

**The one exception — selection-aware subtotals:**
```tsx
// CORRECT — local computation over user-selected subset, labeled as partial
const activeRecords = selectedIds.size > 0
  ? records.filter(r => selectedIds.has(r.id))
  : records;
const footerExtended = activeRecords.reduce((s, r) => s + (r.extended ?? 0), 0);
const selectionLabel = selectedIds.size > 0
  ? `(${selectedIds.size} selected)` : '';
```

### Why Claude Reverts

Claude's training data contains millions of examples of:
- DRF `to_representation` extracting nested values into flat responses
- React components computing their own totals from line arrays
- TypeScript interfaces duplicating backend type definitions
- `SerializerMethodField` as the standard way to add computed fields

These are established patterns in the broader ecosystem. They are wrong for WC3
because WC3 has PJPV — the schema carries behavior end-to-end. Claude doesn't
know this unless told. This readme is that telling.

### The Audit Numbers (2026-08-22)

| Category | Count | Status |
|----------|-------|--------|
| Serializer extractions removed | 6 (Proposal, Order, Purchase × total/margin/margin_pc) | Fixed |
| Serializer envelope fields added | 12 (totals/total/balance × 4 serializers) | Fixed |
| Commission envelope mutation fixed | 1 (RoleAwareModelSerializer) | Fixed |
| React local computations audited | 27 total | 23 legitimate (selection-aware), 1 fixed, 3 dead code |
| React path references updated | 4 files | Fixed |
| Dead code identified | 2 files (OrderLineEditor, InvoiceLineEditor — not imported) | Deleted 2026-08-23 |

## Compliance Enforcement (2026-08-23)

Full compliance audit and schema buildout completed. See `pjpv-process.md` for
the complete arc: what was found, what was fixed, and what was built.

| Milestone | Status | Date |
|-----------|--------|------|
| Totals engine single-owner (`update_received()`) | Done | 2026-08-23 |
| All payment flows through engine | Done | 2026-08-23 |
| Margin formula fixed (subtotal - cost, not total - cost) | Done | 2026-08-23 |
| 21 Pydantic schemas for all envelopes | Done | 2026-08-23 |
| `TransactionTotals` validation in totals engine | **Fail-hard** | 2026-08-23 |
| `LEAF_BEHAVIORS` schema-derived | Done | 2026-08-23 |
| `/wcapi/_pjpv_fields/` endpoint | Done | 2026-08-23 |
| Alice weekly schema review | TODO | — |
| Remaining schemas (ItemPrice, ItemCost, etc.) | Done | 2026-08-23 |
| Promote validation to fail-hard | Done | 2026-08-23 |
| React consuming `/wcapi/_pjpv_fields/` | TODO | — |

## Remaining Shadow Fields

**Terminology updated:** 2026-08-23 — "shadow fields" is the standard term.
**Updated:** 2026-08-24 — removed 13 deleted scalar columns (6 TransactionBaseModel,
4 OrgBase, 3 Contact); 7 shadow fields remain across 5 models.

Shadow fields are scalar database fields that shadow values living authoritatively
in JSON envelopes. They exist because PostgreSQL can efficiently index a
`DecimalField` or `CharField` but cannot efficiently index a key inside a JSONField
for `ORDER BY`, `WHERE`, or aggregate queries.

**Allowed uses:** Database `filter()`, `exclude()`, `order_by()`. List views / DataBrowser
columns. Admin `list_display`.

**Forbidden uses:** Any calculation, any business logic, frontend computation,
serializer extraction, or any place where the value feeds another value. When you need
the value for computation, read the JSON envelope.

### Registry

**TransactionBaseModel** (Order, Proposal, Invoice, Purchase, Workorder):

| Scalar Field | JSON Source | Purpose |
|-------------|-----------|---------|
| `source_name` | `.source` JSON envelope | Query: filter by attribution source |

Removed fields (2026-08-24): `total`, `balance`, `company`, `address_full`, `email`,
`phone`. These are now `@property` methods reading from JSON envelopes.

**OrgBase / Contact:** No shadow fields remain (2026-08-24).

**BillOfMaterial:**

| Scalar Field | JSON Source | Purpose |
|-------------|-----------|---------|
| `parent_description` | `Item.description` (FK) | Display: parent item name in BOM lists |
| `child_ida` | `Item.ida` (FK) | Search: find BOM by component code |
| `child_description` | `Item.description` (FK) | Display: component name in BOM lists |

**InventoryPosition:** Entire model is a rollup of InventoryLayer quantities.

**UserProfile (RBAC):** `cached_roles` shadows `contact.refs.roles` for quick role lookups.

**Setting:** `refs.keywords` denormalized from various config fields for search.

### How the Totals Engine Works

The totals engine (`services/totals.py`) writes only to the `totals` JSONField
envelope — there are no scalar `total` or `balance` columns. Backward-compatible
read access is provided by `@property` methods on TransactionBaseModel. Run
`backfill_totals` to recompute envelopes: `python manage.py backfill_totals --all`

### Alice Shadow Field Enforcement

Alice watches for:
- Direct dict access without `.get()` and a default
- New `DecimalField` with `db_index=True` that shadows a JSONField key without registry entry
- Code assuming `total` or `balance` are database columns (they are `@property` methods)

When a new shadow field is added, it MUST be added to this registry.

---

## Shadow Field Removal (2026-08-24)

Removed all 12 scalar shadow fields from WC3 models in a single session.

### What Was Removed

**TransactionBaseModel:** `total`, `balance` (DecimalField), `company` (CharField),
`address_full`, `email`, `phone` (display cache fields).

**OrgBase:** `address_full`, `phone`, `domain` (3 fields).

**Contact:** `address_full`, `phone`, `domain` (3 fields).

**Fields kept (not shadows):** `Contact.email` (USERNAME_FIELD for auth), `OrgBase.email`
(primary identifier), `TransactionBaseModel.source_name` (standalone dropdown).

### What Replaced Them

**1. PostgreSQL Functional Indexes** for search/filter:
```sql
CREATE INDEX idx_invoice_totals_total ON invoices (((totals->>'total')::numeric));
CREATE INDEX idx_invoice_totals_balance ON invoices (((totals->>'balance')::numeric));
```

Django ORM queries use `common/json_lookups.py` helpers:
```python
from common.json_lookups import totals_total, totals_balance
Invoice.objects.annotate(_bal=totals_balance()).filter(_bal__gt=0)
```

**2. Alice Aggregate Collections** for dashboard `Sum()`:
`apps/ai_assistant/services/aggregate_tracker.py` — delta updates on post_save,
periodic refresh via `python manage.py refresh_aggregates`.

**3. @property Methods** for backward compat:
Each removed field has a read-only `@property` reading from JSON or FK relationships.

### Dual-Write Removed

`totals.py` no longer writes to scalar fields. `update_fields` is now `['totals']` only.

### Bug Fixed

`commerce_dashboard.py` line 308 had `Sum('total')` on Payment (has no `total` field —
it has `amount`). Changed to `Sum('amount')`.

### work_order -> workorder Rename

Also renamed the model registry key from `work_order` to `workorder` to match
Django's `_meta.model_name`. DB table `work_orders` unchanged.

### Files Created

| File | Purpose |
|------|---------|
| `common/json_lookups.py` | `totals_total()`, `totals_balance()`, `totals_received()` ORM helpers |
| `apps/ai_assistant/services/aggregate_tracker.py` | Alice aggregate collections with delta updates |
| `apps/ai_assistant/management/commands/refresh_aggregates.py` | Nightly drift correction command |

---

## History: PJPV Compliance Process (2026-08-23)

### The Problem

PJPV was established 2026-08-22 after discovering three serializers independently
computing margin — one with `Decimal`, one with `float`. The fix on 2026-08-22 removed
serializer extractions but left independent calculations in payment services, signals,
and conversion code untouched. No Pydantic schemas existed for business envelopes.

### Audit Findings

**Backend (14 violations across 9 files):**
- `signals.py`: Bulk `queryset.update()` bypassed totals engine AND versioning (CRITICAL)
- `transaction_save.py`: Wrong margin formula — `total - cost` instead of `subtotal - cost`
- `payment_application.py`: Independent `balance = total - received` in apply/unapply/status
- `payment_pending.py`: Same pattern — direct envelope manipulation
- `conversion.py`: Payment forwarding during order-to-invoice bypassed engine

**React:** Zero critical violations. Two dead-code files deleted.

**Pydantic schemas:** 79 structural schemas existed. ZERO business envelope schemas.

### What Was Fixed

1. Added `update_received()` to `totals.py` — single owner for payment-side balance updates
2. All callers migrated to `update_received()`
3. Margin formula fixed: `subtotal - cost_total` (not `total - cost_total`)
4. Dead React code deleted
5. 21 Pydantic schemas created for all business envelopes in `common/schemas/transaction_envelopes.py`
6. `_validate_totals()` wired into totals engine — fail-hard mode
7. `LEAF_BEHAVIORS` replaced with schema-derived version
8. `/wcapi/_pjpv_fields/` endpoint built

### Schemas Built

| Schema | Fields | Coverage |
|--------|--------|---------|
| `TransactionTotals` | 12 | subtotal through balance |
| `TransactionFinance` | 12 | Tax jurisdiction IDs, rates, amounts |
| `TransactionCost` | 10 | Header-level cost summary |
| `LineQuantity` | 8 | staged/active/remaining + controls |
| `LinePrice` | 7 | unit, base, discount, extended |
| `LineCost` | 16 | unit, extended, surcharges, tax |
| `LineTax` | 6 | Per-line tax rate overrides |
| `LinePhysical` | 9 | weight, dimensions, volume, hazmat |
| `LineItem` | 13 | Denormalized item snapshot |
| `LineCommission` | 3 | Commission envelope |
| `ItemPrice` | 9 | Master pricing |
| `ItemCost` | 8 | Cost tracking |
| `ItemCatalog` | 4 | Categories, attributes |
| `BomOperationalData` | 6 | Operation, work center, setup/run time |
| `OrgAddress/Phone/Email/Domain` | 9/5/5/3 | Unified org communication schemas |

All schemas use `extra = "allow"`. No gaps remain.

### Defense Architecture

| Layer | What it catches | When |
|-------|----------------|------|
| Pydantic validation (L1) | Wrong types, missing keys, out-of-range | At save time |
| `/wcapi/_pjpv_fields/` (L2) | React label/format drift | At render time |
| Alice weekly scan (L3) | Schema-vs-reality drift | Wednesday |
| Claude memory + readme (L4) | Design violations requiring judgment | Every session |

### What Remains

- Alice weekly schema review (not yet scheduled)
- React consuming `/wcapi/_pjpv_fields/` for labels (compliant patterns exist; extending discipline)

---

## Public Site

**pjpv.io** — public-facing site explaining the pattern. Source at `~/Allie/sites/pjpv/`.
GitHub: `https://github.com/JPods/pjpv.git`. Bill owns pjpv.net (first commercial use)
and pjpv.io (developer front door). Hosted on Hostinger.

## See Also

- `readmes/topics/architecture/data-library-ecosystem.md` — Three data types, library model
- Scars #62, #63, #64, #65 — JSON source of truth lessons (leftshoe identity store)
- `common/schemas/transaction_envelopes.py` — The 21 business envelope schemas
- `apps/core/views/schema_fields_view.py` — `/wcapi/_pjpv_fields/` endpoint
- `pjpv.io` — Public site explaining the pattern to developers and capital
