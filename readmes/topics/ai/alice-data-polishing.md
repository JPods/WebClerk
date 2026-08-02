# Alice Data Polishing — Guess, Review, Validate

**Established:** 2026-08-01
**Action:** #31100 (next sprint)
**Dashboard:** db.list at `/db/alice_data_polish` (when built)

---

## The Principle

Better to have a guess than a blank. Blanks are invisible failures. Wrong guesses generate visible corrections. The system learns from corrections, not from blanks.

---

## Three Correction Layers

| Layer | Who | When | What happens |
|-------|-----|------|-------------|
| **1. Alice guesses** | Alice (nightly) | Automated | Fills blank fields with best available data from linked records |
| **2. Admin reviews** | System admin | Morning dashboard | Sees what Alice changed overnight, overrides if wrong |
| **3. Users validate** | Daily users | During work | See wrong data on orders/invoices, complain → correction signal |

Each layer catches what the previous missed. The cost of asking permission first is higher than the cost of a wrong guess — because asking blocks action, while a wrong guess generates a correction that teaches Alice.

---

## What Alice Polishes

### Org ← Contact (most common)

When an Org record (customer, vendor) is missing key fields but its linked contacts have them:

| Org field | Source | How Alice decides |
|-----------|--------|------------------|
| `phone` | Primary contact's phone | Highest-role contact, most recent |
| `email` | Primary contact's email | Same |
| `attention` | Primary contact's display_name | Same |
| `address_full` | Primary contact's address | Same |
| `price_level` | Most recent order's price_level | If org is blank, inherit from transaction history |
| `terms` | Most recent order's terms | Same |

### Contact ← Communications

When a Contact exists but phone/email are in the communications aspect, not on the flat fields.

### Transaction ← Customer

When an order/invoice has `customer_id` but no `company`, `phone`, `attention` populated — Alice fills from the customer's org record + primary contact.

---

## The Nightly Run

Alice runs `alice-data-polish.py` nightly (or as a Celery task):

1. **Scan** — find records with blank key fields
2. **Source** — for each blank, find the best available value from linked records
3. **Score** — assign confidence (high: primary contact phone → org phone; low: old order terms → org terms)
4. **Apply** — write the guess to the blank field
5. **Log** — write a polish record: model, ida, field, old_value, new_value, source, confidence, dt_applied

### Polish Record Schema

```python
{
    "model_name": "customer",       # which model was polished
    "record_id": 5498,              # which record
    "ida": "qqdemo-CUST-05",       # for display
    "field": "phone",              # which field was blank
    "old_value": "",               # was blank
    "new_value": "+16124144211",   # Alice's guess
    "source_model": "contact",     # where Alice found the value
    "source_id": 8,                # which source record
    "source_field": "phone",       # which field on the source
    "confidence": 90,              # 0-100
    "dt_applied": "2026-08-02T07:00:00Z",
    "admin_action": null,          # null=pending, "accepted", "overridden", "reverted"
    "admin_dt": null,
    "user_complaint": null,        # if a user flagged it wrong
}
```

---

## The Dashboard (db.list)

A DataGrid at `/db/alice_data_polish` showing tonight's changes:

**Columns:** model | ida | field | old | new (guess) | source | confidence | action

**Admin actions per row:**
- **Accept** — confirm Alice's guess (stops showing on dashboard)
- **Override** — enter correct value (teaches Alice)
- **Revert** — put back the blank (Alice was wrong to guess)

**Filters:**
- Show all / Pending only / High confidence only
- By model (customer, vendor, contact)
- Date range

**Alice learns from admin actions:**
- Overrides teach Alice better sourcing rules
- Reverts teach Alice which fields should stay blank (e.g., holding companies intentionally have no phone)
- Accepts confirm Alice's heuristics

---

## The User Validation Layer

When a user opens an order and sees wrong data (Alice guessed the wrong phone), they correct it on the order. The order save updates the source record if the user has permission. Alice sees the correction and adjusts her confidence for that source→target pattern.

The user doesn't know Alice guessed. They just see data that needs fixing. That's the point — the correction comes from the person closest to the truth.

---

## What Alice Does NOT Polish

- **Fields with values** — Alice never overwrites existing data
- **Fields marked "intentionally blank"** — admin can flag a field as intentionally empty
- **Sensitive fields** — passwords, API keys, financial account numbers
- **Calculated fields** — totals, margins, balances (those come from transactions)

---

## The Economics

A typical WC3 installation has 5,000-10,000 org records. 30-40% have at least one blank key field. That's 2,000 records Alice can improve in one night.

At $0.50 per manual lookup (find contact, copy phone, paste to org, repeat), that's $1,000 of manual labor Alice does for free on the first night. After that, she polishes incrementally — new records, changed contacts, stale data.

The admin dashboard is the quality control. 10 minutes reviewing 50 changes beats 8 hours of manual cleanup.

---

## Related

- `readmes/topics/ai/pattern-recognition.md` — Alice's observe→log→pattern→recommend→promote loop
- `readmes/topics/architecture/pending-flow-picture.md` — Post or Pend rule (polishes create pending if record is locked)
- Action #31100 — build the dashboard
