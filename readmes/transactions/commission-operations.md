# Commission System — Operations Guide
**Status:** Design complete, oversight service Stage 4 | **Source:** WC2 CM_* / CMA_* mining + Bill 2026-07-04

---

## Principle

WC2 calculated commission live with every action — wasteful. WC3: an oversight function calculates periodically. We are guides, not policemen. Report commissions, don't compute on every keystroke.

---

## What Already Exists

| Field | On | Purpose |
|---|---|---|
| `is_commission` | TransactionBaseModel | True = this is a commission-payable transaction (rep invoices manufacturer) |
| `commission` | TransactionBaseModel (JSON) | Flexible object: rep info, rate, calculated amount, can even contain a script |
| `price_level` | TransactionBaseModel + OrgBase | Drives commission rate (rate varies by price point) |

No new models needed initially. The `commission` JSON handles the data. CommissionRule and CommissionEntry models can come later if the JSON approach proves insufficient.

---

## The Rep Workflow (Trade Show Example)

```
Rep at trade show takes order from Customer for 3 manufacturers:
  Wilson (bat), Rawlings (glove), In-House (baseballs)

Step 1: Rep creates one master order
Step 2: System splits into 3 orders:
  ├── Order A → Wilson (is_commission=False, shipped by Wilson)
  ├── Order B → Rawlings (is_commission=False, shipped by Rawlings)  
  └── Order C → In-House (is_commission=False, normal product order)

Step 3: Rep invoices manufacturers for commission:
  ├── Invoice to Wilson (is_commission=True, commission on bat sale)
  └── Invoice to Rawlings (is_commission=True, commission on glove sale)

Step 4: Customer invoiced for product:
  └── Invoice to Customer (is_commission=False, product invoice)
```

The `is_commission` flag separates commission invoices from product invoices. Reports can filter by flag. GL journals post to different accounts (commission expense vs revenue).

---

## Commission JSON Structure

```json
transaction.commission = {
  "reps": [
    {
      "rep_id": 42,
      "rep_name": "Smith Sales",
      "rate": 0.10,
      "rate_basis": "wholesale",
      "amount": 125.50,
      "manufacturer_id": 15,
      "accrued": false,
      "dt_calculated": 1720100000000
    }
  ],
  "total": 125.50,
  "accrued": false,
  "dt_accrued": null
}
```

---

## Commission Rate Determination

```
Rate varies by:
  1. Rep (each rep has a negotiated base rate)
  2. Manufacturer (some manufacturers pay higher commissions)
  3. Price level (commission may differ at wholesale vs retail)
  4. Item (specific items may have custom commission rates)

Resolution: rep.rate × price_level_factor × manufacturer_factor
  → stored in commission JSON at time of calculation
  → does NOT recalculate on every save
```

---

## Oversight Service (to be built — Stage 4)

```python
def calculate_commissions(period_start, period_end):
    """Batch calculate commissions for all un-calculated transactions in period.
    
    Reads: transaction lines, rep assignments, rate tables
    Writes: transaction.commission JSON
    Reports: commission by rep, by manufacturer, by period
    """
```

Called periodically (weekly, monthly) — not on every save. Alice can run this and report.

---

## GL Integration

Already built in `journalize.py`:
- `journalize_invoice` checks for `commission.reps` and calls `accrue_commission`
- Commission posts to commission expense GL account
- Separate from product revenue posting

---

## Reporting (Commerce Dashboard)

Sales tab and Sales by Salesperson report already carry the structure:
- Revenue by rep
- Margin by rep
- Commission amount by rep (from commission JSON)

---

## What WC2 Had (22 CMA_* methods)

WC2's commission system handled:
- Complex multi-manufacturer order import
- Order splitting by manufacturer
- Commission invoice generation
- Payment tracking (commission payments from manufacturers)
- Rate lookup by rep × price level

Most of this was import/export machinery for specific customers (Abbott, etc.). The core business logic is: rate × sale amount = commission. WC3's flexible JSON + oversight service covers this without 22 dedicated methods.

---

## Files

| File | Purpose |
|------|---------|
| `apps/transactions/models/base_transaction_model.py` | is_commission flag + commission JSON |
| `apps/accounts/services/journalize.py` | accrue_commission on journal posting |
| `apps/transactions/services/commission.py` | Commission accrual service (exists) |
