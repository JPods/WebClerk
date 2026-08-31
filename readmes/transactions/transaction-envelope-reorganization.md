# Transaction Header Envelopes — PJPV Schema Map

**Status:** Implemented | **Date:** 2026-08-30

## Principle

**`totals` holds the arithmetic result. Domain envelopes hold the detail that produced it.**

`totals.shipping` = the dollar charge (part of the arithmetic chain).
`shipping` = carrier, packages, tracking, weight (the logistics that produced the charge).

## Header Envelopes

Every transaction header carries these JSON envelopes. Each has a Pydantic
schema in `common/schemas/transaction_envelopes.py` registered in
`ENVELOPE_SCHEMA_MAP`.

| Field | Schema | What it holds |
|-------|--------|---------------|
| `totals` | `TransactionTotals` | Financial arithmetic — computed by ONE engine (`recalculate_totals`) |
| `finance` | `TransactionFinance` | Tax jurisdiction config, collection/exchange expenses |
| `cost` | `TransactionCost` | Header cost summary — line sums, freight, handling, commissions |
| `tax` | `TransactionTax` | Tax rates and amounts (sell-side + cost-side), tax engine link |
| `commission` | `TransactionCommission` | Rep commissions — total, split, basis, method |
| `flow` | `TransactionFlow` | Transaction lineage — source[] and children[] |
| `source` | `TransactionSource` | Attribution — campaign, catalog, vendor, manufacturer |
| `actions` | `TransactionAction` | Next-action tracking (who/when/what) |
| `shipping` | `TransactionShipping` | Logistics — carrier, packages, costs, weight, fulfillment |

## Line Envelopes

Lines carry their own schemas — these feed the header:

| Field | Schema | Feeds |
|-------|--------|-------|
| `quantity` | `LineQuantity` | staged/active/remaining + controls |
| `price` | `LinePrice` | → sums to `totals.subtotal` |
| `cost` | `LineCost` | → sums to `totals.cost` |
| `tax` | `LineTax` | → sums to `totals.tax` |
| `physical` | `LinePhysical` | → sums to `shipping.gross_weight` |
| `item` | `LineItem` | Denormalized item snapshot |
| `commission` | `LineCommission` | → sums to header `commission.total` |

## ENVELOPE_SCHEMA_MAP

16 entries total — used by `field_behaviors.py` to generate LEAF_BEHAVIORS
from schemas instead of maintaining a parallel hardcoded dict.

```python
ENVELOPE_SCHEMA_MAP = {
    # Transaction header envelopes
    'totals': TransactionTotals,
    'finance': TransactionFinance,
    'header_cost': TransactionCost,
    'header_tax': TransactionTax,
    'header_commission': TransactionCommission,
    'flow': TransactionFlow,
    'source': TransactionSource,
    'actions': TransactionAction,
    'shipping': TransactionShipping,
    # Line-level envelopes
    'quantity': LineQuantity,
    'price': LinePrice,
    'cost': LineCost,
    'tax': LineTax,
    'physical': LinePhysical,
    'item': LineItem,
    'commission': LineCommission,
}
```

## Files

| File | What |
|------|------|
| `common/schemas/transaction_envelopes.py` | All Pydantic schemas + ENVELOPE_SCHEMA_MAP |
| `apps/transactions/models/base_transaction_model.py` | Default factories + JSONField declarations |
| `apps/transactions/models/base_line_model.py` | Line-level default factories |
| `apps/transactions/services/pricing/totals_compute.py` | The ONE totals engine |
