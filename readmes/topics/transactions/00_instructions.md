# Transaction Plan — Overview & Index

> **Purpose**: Master document for the transaction subsystem.  
> Organized by the org-relationship roles that drive each document type.

---

## 1. Core Principle

Every transaction exists because two organizations (or an org and a consumer) are
exchanging **activity → documents → money**.  The document type is determined by
the *role* the organization plays in the relationship, and lines share a strong
common base that specializes per side.

---

## 2. Model Hierarchy

```
CoreModel              (id BigAutoField, uuid, ida, dt_created, dt_modified, version, is_active)
 └─ BaseModel          (display_name, notes, metadata JSON, refs JSON, prefs JSON)
     ├─ TransactionBaseModel   (total, balance, status, customer FK, vendor FK, manufacturer FK,
     │                          contact FK, terms, totals JSON, cost JSON, sell JSON, finance JSON,
     │                          flow JSON, source JSON, actions JSON, parent_id, parent_model)
     │   ├─ Proposal
     │   ├─ Order
     │   ├─ Invoice
     │   ├─ Purchase
     │   ├─ WorkOrder
     │   ├─ Requisition
     │   └─ Project
     ├─ Receipt          (extends BaseModel directly — not TransactionBaseModel)
     ├─ Payment          (extends BaseModel — invoice FK, amount, gateway fields, status)
     ├─ PaymentTerm      (extends BaseModel — name, days, is_active)
     ├─ PaymentMethod    (extends BaseModel — name, is_active)
     └─ PaymentApplication (extends BaseModel — payment FK, invoice FK, amount)
```

### Line Hierarchy

```
BaseLineCore (BaseModel)         item_fk FK→Item, item JSON, quantity JSON, cost JSON, tax JSON, physical JSON
 ├─ BaseSellLineModel            + price JSON  →  ProposalLine, OrderLine, InvoiceLine
 └─ BaseExecLineModel            (no price)    →  PurchaseLine, WorkOrderLine, RequisitionLine, ReceiptLine
```

**Key**: Sell-side lines carry a `price` JSON (what the customer pays); exec-side
lines do not — they track cost only.

### Line FK Convention

Each concrete line FK is named after its parent model (singular, lowercase):

| Line Model       | FK field      | Points to   |
|-------------------|---------------|-------------|
| `ProposalLine`    | `proposal`    | `Proposal`  |
| `OrderLine`       | `order`       | `Order`     |
| `InvoiceLine`     | `invoice`     | `Invoice`   |
| `PurchaseLine`    | `purchase`    | `Purchase`  |
| `WorkOrderLine`   | `workorder`   | `WorkOrder` |
| `RequisitionLine` | `requisition` | `Requisition` |
| `ReceiptLine`     | `receipt`     | `Receipt`   |

All lines expose `@property parent` and `@property parent_id_value` for
uniform access regardless of concrete FK name.

---

## 3. Identity — `id` and `ida`

| Field | Type | Scope |
|-------|------|-------|
| `id`  | `BigAutoField` (PK) | **Per-table** PostgreSQL sequence — each concrete model increments independently |
| `ida` | `CharField(40)` | Auto-set to `str(pk)` on first save (`CoreModel.save()`). Also independent per model. Project policy can override per-model later. |

There is **no shared sequence** across transaction types.  Proposal #5 and
Order #5 are unrelated identities.

---

## 4. Transaction Flow by Organization Role

### 4a. Customer Org — Sell Side

The customer-facing pipeline converts **activity into revenue**:

```
Proposal  →  Order  →  Invoice  →  Ledger  →  Payment
(offer)     (promise)  (deliver)   (schedule)  (collect)
```

| Stage | Model | Purpose | Lines |
|-------|-------|---------|-------|
| **Proposal** | `Proposal` | Offer to sell goods/services at stated prices | `ProposalLine` (BaseSellLineModel) |
| **Order** | `Order` | Confirmed commitment to sell; triggers inventory reservation | `OrderLine` (BaseSellLineModel) |
| **Invoice** | `Invoice` | Delivery on the promise; payment expected per terms | `InvoiceLine` (BaseSellLineModel) |
| **Ledger** | `Ledger` (apps/accounts) | Breaks invoice into specific obligations on specific due dates, driven by `PaymentTerm` | — |
| **Payment** | `Payment` + `PaymentApplication` | Customer payment that liquidates ledger obligations | — |

**Transfer services** (sell side):

| Service | File |
|---------|------|
| Proposal → Order | `services/proposal_to_order.py` |
| Order → Invoice | `services/order_to_invoice.py` |

**Totals services** (sell side):

| Service | File |
|---------|------|
| Proposal totals | `services/proposal_totals.py` |
| Order totals | `services/order_totals.py` |
| Invoice totals | `services/invoice_totals.py` |

### 4b. Vendor Org — Exec Side

The vendor-facing pipeline **converts commitments into fulfilled purchases**:

```
Purchase  →  Receipt
(promise)    (acknowledge)
```

| Stage | Model | Purpose | Lines |
|-------|-------|---------|-------|
| **Purchase** | `Purchase` | Promise to buy from a vendor at agreed cost | `PurchaseLine` (BaseExecLineModel) |
| **Receipt** | `Receipt` | Acknowledges vendor delivery / invoice / obligation. Drives inventory-in. | `ReceiptLine` (BaseExecLineModel) |

A Purchase may originate from an Order (drop-ship or procurement) or be created
directly.

**Receipt** extends `BaseModel` (not TransactionBaseModel) and has:
- `source_type`: `purchase_receipt` | `workorder_completion` | `inventory_adjustment`
- Optional FKs to `Purchase` and `WorkOrder`

**Transfer services** (exec side):

| Service | File |
|---------|------|
| Order → Purchase | `services/order_to_purchase.py` |
| Proposal → Purchase | `services/proposal_to_purchase.py` |
| Purchase → Order | `services/purchase_to_order.py` |
| Purchase → Proposal | `services/purchase_to_proposal.py` |
| Purchase → Invoice | `services/purchase_to_invoice.py` |
| Invoice → Purchase | `services/invoice_to_purchase.py` |

**Totals services** (exec side):

| Service | File |
|---------|------|
| Purchase totals | `services/purchase_totals.py` |
| PO totals | `services/po_totals.py` |
| Work Order totals | `services/wo_totals.py` |

### 4c. Manufacturer Org

A manufacturer may be **invoiced for commissions** earned on transactions
they are associated with as a party.  The manufacturer FK on
`TransactionBaseModel` links the manufacturer org to the transaction.

> Commission calculation logic is documented separately in
> [commissions.md](commissions.md).

### 4d. Rep Org / Contact

A rep (sales representative) may **earn commission** for supporting
proposals, orders, or invoices.  Rep association is tracked via
the contact FK or metadata on the transaction.

> Commission calculation logic is documented separately in
> [commissions.md](commissions.md).

---

## 5. WorkOrder & Requisition

| Model | Base | Purpose |
|-------|------|---------|
| `WorkOrder` | `TransactionBaseModel` | Internal manufacturing/assembly instructions |
| `Requisition` | `TransactionBaseModel` | Internal material request; may feed into Purchase |

Both use `BaseExecLineModel` lines (no sell price).  WorkOrder completion
creates a `Receipt` with `source_type = workorder_completion`.

---

## 6. Shared JSON Envelopes

### Header (TransactionBaseModel)

| JSON field | Purpose | Default factory |
|------------|---------|-----------------|
| `totals` | Flat searchable totals: subtotal, discount, taxable, tax, shipping, other, total, cost, margin, margin_pc, received, balance | `default_totals()` |
| `cost` | Cost rolled up from lines: line_sum_goods, freight, commissions, total, etc. | `default_cost()` |
| `sell` | Reserved for sell-side aggregates | `dict` |
| `finance` | Tax details: sales_tax_rate, cost_tax_rate, exchange_expense, etc. | `default_finance()` |
| `flow` | Source/children linkage for transfer tracing | `default_transaction_flow()` |
| `source` | Campaign, catalog, vendor, manufacturer IDs | `default_source()` |
| `actions` | Next-action tracking | `default_action()` |

### Line (BaseLineCore)

| JSON field | Purpose | Default factory |
|------------|---------|-----------------|
| `item` | Denormalized item snapshot: item_id, ida_item, description, sequence, line_number | `default_item()` |
| `quantity` | placed, actioned, remaining, is_fixed, precision; keys vary by transaction kind | `default_quantity(kind)` |
| `cost` | unit, unit_base, discount_percent/amount, extended, shipping, handling, freight, commissions, tax | `default_cost()` |
| `price` | **(BaseSellLineModel only)** unit, unit_base, discount_percent/amount, extended | `default_price()` |
| `tax` | sales_rate, sales, cost_rate, cost, shipping, tax_service_id | `default_tax()` |
| `physical` | weight, dimensions, volume, package_count, is_hazmat | `default_physical()` |

---

## 7. Accounts Pipeline

### Ledger (`apps/accounts/models/ledger.py`)

Ledger entries are the bridge between invoicing and payment.  An invoice's
payment terms generate one or more ledger rows, each with:

- `value_original` — scheduled amount
- `value_available` — remaining balance (decremented by payments)
- `dt_due` — due date for this installment
- `dt_discount_due` — early-payment discount deadline
- `discount_potential` — discount amount if paid early
- `invoice` FK → `Invoice`
- `term` FK → `Term`
- `gl_account` FK → `GlAccount`
- Status flags: `is_settled`, `is_cleared`, `is_void`

### Payment → Ledger Settlement

`PaymentApplication` links a `Payment` to an `Invoice` with an applied amount.
The `payment_application.py` service orchestrates:

1. Validate payment amount vs invoice balance
2. Create `PaymentApplication` record
3. Update `Ledger.value_available`
4. Update `Invoice.totals.received` and `Invoice.totals.balance`

---

## 8. Inventory Flow

Inventory changes are triggered by transaction state changes:

| Trigger | Effect |
|---------|--------|
| Order confirmed | Reserve inventory (pending allocation) |
| Invoice created from order | Consume reservation, decrement on-hand |
| Receipt created from purchase | Increment on-hand |
| WorkOrder completion receipt | Increment finished goods |

Processed by `services/inventory_flow.py` and `services/pending_inventory_processor.py`.
Background dispatch via Celery — see `readmes/topics/infrastructure/celery-redis-pending.md`.

---

## 9. Known Issues

Documented in `readmes/09-transaction-calc-status.md`:

1. **Quantity key mismatch**: React2025 sends `ordered`, backend reads `placed` — extended = 0.
   Transfer services also use legacy keys (`ordered`, `invoiced`, `packed`).
   Canonical keys are `placed` / `actioned` / `remaining` per `default_quantity()`.
   See `transaction_flow_test_plan.md` §8 for the alignment action items.
2. **Header totals signal gap**: Only `ProposalLine` has a post-save signal for totals recalculation; Order/Invoice/Purchase lines do not.
   See `transaction_flow_test_plan.md` §4b for status.

---

## 10. Related Documents

### In this folder (`topics/transactions/`)

| File | Content |
|------|---------|
| `transaction_flow_plan.md` | Phase-by-phase implementation plan (uses some legacy naming) |
| `transaction_flows.md` | Detailed flow diagrams and rules (uses some legacy naming) |
| `transaction-flow-responsibilities.md` | Frontend vs. backend responsibility matrix |
| `transactions-totals.md` | Totals rollup architecture (sell + cost sides) |
| `transaction_line_save.md` | Line-save architecture and normalization |
| `transaction_flow_calc_plan.md` | Salvaging WC2 calculation logic |
| `terms-ledgers.md` | Terms → ledger scheduling |
| `proposal_submission_flow.md` | Proposal-specific submission workflow |
| `currency-updates.md` | Multi-currency handling |
| `commissions.md` | Commission calculation (stub) |
| `transaction_flow_test_plan.md` | Test plan: FK, lineage, quantity flow, totals, e2e |

### Elsewhere

| File | Content |
|------|---------|
| `readmes/09-transaction-calc-status.md` | Quantity key mismatch + totals signal gap |
| `readmes/topics/infrastructure/celery-redis-pending.md` | Celery/Redis dispatch architecture |
| `readmes/topics/inventory/` | Inventory model and flow docs |

---

## 11. Transfer Services — Full Map

```
           ┌──────────┐
           │ Proposal │
           └────┬─────┘
        ┌───────┴───────┐
        ▼               ▼
   ┌─────────┐    ┌──────────┐
   │  Order  │ -> │ Purchase │
   └────┬────┘    └─────┬────┘
        │               │
        ▼               ▼
   ┌─────────┐    ┌──────────┐
   │ Invoice │    │ Receipt  │
   └────┬────┘    └──────────┘
        │
        ▼
   ┌─────────┐    ┌──────────┐
   │ Ledger  │───▶│ Payment  │
   └─────────┘    └──────────┘
```

Cross-side transfers also exist (Purchase ↔ Order, Purchase ↔ Invoice,
Purchase → Proposal) for vendor-sourced fulfillment scenarios.