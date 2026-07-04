# Source Attribution — Operations Guide
**Built:** 2026-07-04

---

## Overview

Every Contact and transaction (Order, Invoice, Proposal, Purchase, WorkOrder) has a `source_name` field — a simple dropdown for tagging where it came from. Provide the tool, if they use it great. Low friction, high value.

---

## Two Levels

```
source_name = "Facebook"           ← simple field, dropdown, low friction
source = {                         ← rich JSON for sophisticated tracking
    campaign_id: 42,
    medium: "social",
    content: "summer-promo"
}
```

Most users use `source_name`. Power users populate both.

---

## Where It Lives

| Model | Field | Purpose |
|---|---|---|
| Contact | `source_name` | Where did this customer come from? |
| Order | `source_name` | What drove this order? |
| Invoice | `source_name` | Inherited from order or set directly |
| Proposal | `source_name` | What drove this quote? |
| Purchase | `source_name` | (Less common — internal attribution) |
| WorkOrder | `source_name` | What drove this job? |

All are `CharField(max_length=80, db_index=True)`. Sortable, filterable in DataBrowser.

---

## Dropdown Options

Options come from bootstrap select list `source_attribution` — not hardcoded. Admin adds/removes sources via Setting record. Examples:

- Facebook, Google, Instagram, LinkedIn
- Referral, Walk-in, Phone Call, Trade Show
- Website, Email Campaign, Direct Mail
- Repeat Customer, Cross-sell

---

## Attribution Chain

When populated:

```
Campaign ($5,000 Facebook ad)
  → Contact.source_name = "Facebook"
    → Order.source_name = "Facebook" (inherited or set)
      → Invoice → payment → lifetime value
        = Campaign ROI
```

Alice can report: "Facebook drove 12 contacts, 8 orders, $45,000 revenue. ROI: 9:1."

---

## Alice's Role

Alice does NOT nag at entry time. After the fact:
> "You left 15 orders unassigned. Do you want me to open them so you can add source?"

Batch coaching, not per-record friction.

---

## Files

| File | Purpose |
|------|---------|
| `apps/transactions/models/base_transaction_model.py` | source_name on all transactions |
| `apps/core/models/contact.py` | source_name on Contact |
