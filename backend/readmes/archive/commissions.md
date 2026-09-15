# Commissions

> **Status**: Stub — calculation logic TBD.

---

## Overview

Commissions represent earnings owed to parties (reps, manufacturers) based
on their role in a transaction.  Two primary scenarios exist:

### 1. Rep Commissions

A sales representative supports the sell-side pipeline (Proposal → Order →
Invoice).  The rep may earn a percentage of the sell value or margin.

- **Association**: via `contact` FK or `metadata.refs` on the transaction header
- **Trigger**: typically calculated when an Invoice is created or paid
- **Output**: commission amount stored in line `cost.commissions` and/or
  header `cost.commissions`

### 2. Manufacturer Commissions

A manufacturer may owe or be owed commissions based on sales of their
products.  The manufacturer FK on `TransactionBaseModel` links the
manufacturer org to each transaction.

- **Association**: `manufacturer` FK on `TransactionBaseModel`
- **Trigger**: TBD — possibly at Invoice or Payment stage
- **Output**: TBD

---

## Open Questions

1. Commission rate source — per-rep, per-manufacturer, per-item, per-price-level?
2. When is commission calculated — on invoice creation, on payment, or both?
3. How are commission payouts tracked — separate transaction type, or ledger entries?
4. Split commissions — can multiple reps share a transaction?
5. Relationship to `cost.commissions` field on line and header models

---

## Related

- [00_instructions.md](00_instructions.md) — Transaction plan overview (§4c, §4d)
- `apps/transactions/models/base_line_model.py` — `cost.commissions` field
- `apps/transactions/models/base_transaction_model.py` — `cost.commissions` field, manufacturer FK
