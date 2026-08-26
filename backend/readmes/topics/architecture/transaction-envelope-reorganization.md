# Transaction Envelope Reorganization — Plan

**Status:** Plan — not yet implemented
**Date:** 2026-08-26
**Context:** We built `TransactionShipping` as a proper PJPV envelope. That exposed
the scattered state of the other transaction envelopes. Bill asked: if shipping has
its own object, shouldn't tax, commission, and the rest? And what about transaction lines?

## The Principle

**`totals` holds the arithmetic result. Domain envelopes hold the detail that produced it.**

`totals.shipping` = the dollar charge (part of the arithmetic chain).
`shipping` = carrier, packages, tracking, weight (the logistics that produced the charge).

Same pattern applies to tax, commission, and every other domain.

## Current State — Transaction Headers

| Field | What it holds now | Schema | Problem |
|-------|------------------|--------|---------|
| `totals` | Financial arithmetic + some detail | `TransactionTotals` | Clean — keep as-is |
| `finance` | Tax config + collection/exchange expenses | `TransactionFinance` | Tax config should be in `tax`; finance should be payment/GL |
| `commission` | Commission data | `dict` (no schema) | Needs schema |
| `flow` | Workflow state | `dict` (no schema) | Needs schema |
| `source` | Campaign/origin | `dict` (no schema) | Needs schema |
| `shipping` | Logistics | `TransactionShipping` | Just built — correct |

## Current State — Transaction Lines

| Field | What it holds now | Schema | Problem |
|-------|------------------|--------|---------|
| `quantity` | ordered, shipped, backordered, received | `LineQuantity` | Good |
| `price` | unit, unit_base, extended, discount | `LinePrice` | Good |
| `cost` | unit, extended, margin | `LineCost` | Good |
| `tax` | tax amount, rate, jurisdiction per line | `LineTax` | Good |
| `physical` | weight, dimensions, hazmat | `LinePhysical` | Good |
| `item` | item snapshot (ida, name, uom) | `LineItem` | Good |
| `commission` | rep, rate, amount per line | `LineCommission` | Good |

Lines are in better shape — they already have schemas. The gap is on the header side.

## Proposed Structure — Transaction Headers

### `totals` — arithmetic only (no change)

Stays exactly as-is. Pure computed values from one engine.

```
subtotal, discount, taxable, tax, shipping, other, total, balance,
cost_total, cost_tax, margin_amount, margin_pct
```

### `tax` — NEW header envelope

Tax configuration and compliance detail. The dollar amounts stay in
`totals.tax` and `totals.cost_tax`.

```
sales_jurisdiction_id    FK to tax_jurisdiction
sales_jurisdiction_name  display name
sales_rate               decimal rate (0.0825)
sales_amount             computed (mirrors totals.tax)
cost_jurisdiction_id     FK to tax_jurisdiction
cost_jurisdiction_name   display name  
cost_rate                decimal rate
cost_amount              computed (mirrors totals.cost_tax)
exempt                   boolean — customer is tax exempt
exempt_certificate       certificate number
exempt_reason            why exempt
nexus_state              state where nexus applies
```

**Migration from `finance`:** Move `sales_tax_id`, `sales_tax_name`,
`sales_tax_rate`, `sales_tax`, `cost_tax_id`, `cost_tax_name`,
`cost_tax_rate`, `cost_tax`, `tax_subtotal`, `tax_pc` out of `finance`
into `tax`.

### `commission` — NEW header envelope

Commission rules and summary for the transaction.

```
rep_id                   FK to rep/contact
rep_name                 display name
rate                     commission rate
method                   flat | percentage | tiered
amount                   computed commission amount
split                    [{rep_id, rate, amount}] for split commissions
basis                    what commission is calculated on (subtotal, margin, total)
```

### `finance` — SLIMMED (after tax moves out)

Payment terms, GL, credit, and financial metadata.

```
terms_id                 FK to payment_term
terms_name               display name
due_date                 computed from terms + invoice date
gl_account_id            FK to gl_account
gl_account_name          display name
credit_limit             customer credit limit snapshot
credit_available         available credit at time of order
collection_expense       collection costs
exchange_expense         currency exchange costs
currency                 transaction currency code
exchange_rate            rate to base currency
```

### `shipping` — ALREADY BUILT

Carrier, packages, tracking, weight, costs, fulfillment dates.

### `flow` — NEW header envelope

Workflow state and lifecycle.

```
status                   current workflow status
stage                    pipeline stage
assigned_to              who owns this transaction
priority                 urgency level
dt_submitted             when submitted for approval
dt_approved              when approved
dt_released              when released to warehouse/fulfillment
approved_by              who approved
hold_reason              if on hold, why
```

### `source` — NEW header envelope

Origin and attribution.

```
campaign_id              FK to campaign/project
campaign_name            display name
catalog_id               FK to catalog
vendor_id                originating vendor
manufacturer_id          originating manufacturer
channel                  web, phone, email, walk-in, EDI
referral                 referral source
ad_source                advertising source
```

## Transaction Lines — Keep Together

Lines are computational inputs to the parent transaction. A line has one tax
rate, one commission, one set of amounts. The complexity that justifies
separate envelopes lives at the header level (jurisdiction rules, exemption
certificates, split commissions, carrier logistics). Lines just contribute
numbers upward.

**Decision:** Lines keep tax, commission, quantity, price, cost in the same
object. These are fine as separate JSON fields on the line model because
each is small and flat. No reorganization needed.

Lines feed the header:
- line.price.extended → sums to totals.subtotal
- line.tax.amount → sums to totals.tax
- line.commission.amount → sums to header commission.amount
- line.cost.extended → sums to totals.cost_total
- line.physical.weight → sums to shipping.gross_weight

The line schemas (LineQuantity, LinePrice, LineCost, LineTax, LinePhysical,
LineItem, LineCommission) are already correct. Only review needed:

| Schema | Review item |
|--------|------------|
| `LinePrice` | `unit` name collision with item.unit (uom) — already identified |
| `LineQuantity` | Verify covers purchase vs sales semantics |

## Migration Strategy

This is a data migration, not just a schema change. Existing JSON data
in `finance` needs to move to `tax`. Options:

### Option A — Lazy migration (recommended)

1. Create new schemas (`TransactionTax`, `TransactionCommission`, etc.)
2. Add to ENVELOPE_SCHEMA_MAP and LEAF_MAP
3. Backend reads from new location, falls back to old
4. On any save, migrate data to new location automatically
5. Management command to batch-migrate existing records
6. After migration complete, remove fallback reads

### Option B — Big bang migration

1. Create schemas
2. Write Django migration that moves JSON data in-place
3. Update all code at once

Option A is safer — records migrate gradually, no downtime, fallback if anything breaks.

## Order of Work

1. **TransactionTax** — move tax config from finance, add exempt/nexus fields
2. **TransactionCommission** — header commission with split support
3. **Slim finance** — remove migrated fields, add payment/GL fields
4. **TransactionFlow** — workflow state
5. **TransactionSource** — attribution
6. **Line review** — verify all line schemas against all transaction types
7. **Setting Parade** — verify all new envelopes show correctly
8. **LEAF_MAP** — add new envelopes to all transaction models
9. **Totals engine** — verify it still reads from `totals` only (it should — no change needed)

## What NOT to Change

- `totals` structure — don't move dollar amounts out
- `totals` computation engine — it reads `totals`, not the domain envelopes
- Line-level schemas — they're already correct, just need review
- The principle: computed summary in `totals`, domain detail in its own envelope

## Risk

- **Data migration** — moving JSON keys within live records
- **Field behavior regeneration** — LEAF_MAP changes mean Settings need rebuild
- **Frontend caching** — PJPV catalog is cached per session; new envelopes won't show until refresh
- **Report/print templates** — any template reading `finance.sales_tax_rate` needs update
