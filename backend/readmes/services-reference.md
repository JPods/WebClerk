# WebClerk3 Services Reference

All backend services follow the same pattern: single-purpose functions, called from `wcapi/manage`, returning dicts. WebClerk is commerce, not accounting -- we produce GL journal entries; accounting programs consume them.

---

## Accounting

### journalize.py

**File:** `apps/accounts/services/journalize.py`
**Purpose:** Line-level GL posting for invoices, payments, and purchases.

| Function | Signature | Description |
|----------|-----------|-------------|
| `journalize_invoice` | `(invoice_id: int, ida_prefix: str = '') -> dict` | Walk each invoice line, post AR/Revenue/COGS/Inventory entries. Consolidates by GL account. FX rounding auto-absorbed < $2. Auto-accrues commission if present. Marks invoice `is_locked=True`. |
| `journalize_payment` | `(payment_id: int, ida_prefix: str = '') -> dict` | Cash debit, AR credit. Resolves customer GL overrides. Zero-amount payments auto-complete without GL (H10). Hold payments skipped (H11). |
| `journalize_purchase` | `(purchase_id: int, ida_prefix: str = '') -> dict` | Inventory debit, AP credit per purchase line. Uses item.gls for account resolution. FX rounding auto-absorbed < $2. |
| `batch_journalize` | `(ida_prefix: str = 'zzz-') -> dict` | Find all un-journalized documents and journal them. Returns `exceptions[]` (out-of-balance, require user action) and `skipped[]` (hold, zero-amount) separately from successful postings. |
| `force_to_balance` | `(source_id, source_model, user_statement, forced_by, adjustment_account) -> dict` | Force an out-of-balance journal to balance by adding an adjusting line. **Requires user statement** (min 10 chars) explaining why. |

**Balance check (WC2 GL1 + GL2 rules):**
Every journal is balance-checked before posting. If debits != credits:
1. **FX auto-absorption** — if the document has a foreign exchange rate and residual < $2, the difference is absorbed into `MISC-FXROUNDING-000` automatically (WC2 GL2 rule).
2. **Exception** — if residual >= $2 or no exchange rate, the journal is flagged as an exception with `status='exception'` and returned to the dashboard for user action.
3. **ForceToBalance** — user reviews the exception, provides a statement (e.g., "rounding error on very low cost item"), and calls `force_to_balance()`. The adjusting line is posted with the user's statement as audit trail.

**ForceToBalance audit trail (stored in three places):**
1. `GlJournal.note` on the adjusting line — the user's statement
2. `GlJournal.metadata` on the adjusting line — full audit record (who, when, residual amount, adjustment account)
3. Source transaction `metadata.gl_accounts.force_balance[]` — array of all force-balance events for this document

**Payment special cases (WC2 GL_JrnlCash rules):**
- **Zero-amount** (H10): Adjusting entries and memo credits are marked `is_locked=True` and `metadata.gl_accounts.posted=True` immediately with no GL lines. Prevents unbalanced $0 journals from blocking the batch.
- **Hold status** (H11): Payments with status starting with "hold" are skipped entirely. Disputed payments do not post until status changes.

**Manage actions:** `journalize_invoice`, `journalize_payment`, `journalize_purchase`, `batch_journalize`, `force_to_balance`

**GL accounts written:**

| Journal Type | Debit | Credit |
|-------------|-------|--------|
| Sales (invoice) | AR (customer override or `ASSET-AR-000`) | Revenue (item.gls.revenue or `REV-SALES-000`) |
| Sales (COGS) | COGS (item.gls.cogs or `COGS-PRODUCTS-000`) | Inventory (item.gls.inventory or `ASSET-INVENTORY-000`) |
| Cash (payment) | Cash (customer override or `ASSET-CASH-000`) | AR (customer override or `ASSET-AR-000`) |
| Purchase | Inventory (item.gls.inventory or `ASSET-INVENTORY-000`) | AP (item.gls.purchase or `LIAB-ACCTSPAY-000`) |
| FX Absorption | — | `MISC-FXROUNDING-000` (or debit, depending on residual sign) |
| ForceToBalance | — | User-specified or `MISC-FXROUNDING-000` default |

**Settings/Config:** Default GL accounts hardcoded in `DEFAULTS` dict. FX absorption threshold in `FX_ABSORPTION_LIMIT` ($2.00). Customer overrides via `OrgBase.gl_accounts`. Item-level overrides via `Item.gls`.

**Dependencies:** Calls `accrue_commission()` from commission service after invoice journalization (non-blocking -- commission failure does not block invoice posting).

**Guards:** Double-posting prevented by `GlJournal.objects.filter(source_id, source_model).exists()`. Balance verification via `_check_balance()` with FX absorption before writing. ForceToBalance requires minimum 10-character user statement.

---

## Transactions

### commission.py

**File:** `apps/transactions/services/commission.py`
**Purpose:** Calculate, assign, and accrue commissions on transactions.

| Function | Signature | Description |
|----------|-----------|-------------|
| `empty_commission` | `() -> dict` | Empty commission schema for header/line. |
| `empty_rep_entry` | `(rep_id, rep_ida, name, rate_pct, split_pct, level_factor, basis) -> dict` | One rep's commission entry with effective_rate calculated. |
| `get_rep_commission_config` | `(rep_id: int) -> dict` | Load rate_pct, basis, level_factors from rep's OrgBase record. |
| `get_customer_rep_ids` | `(customer_id: int) -> list[int]` | Get rep IDs from customer.refs.links.reps or customer.relations. |
| `calculate_line_commission` | `(line_price_extended, line_cost_extended, price_level, rep_configs, basis_override) -> dict` | Calculate commission for one line. |
| `populate_transaction_commission` | `(transaction_id: int, model_name: str) -> dict` | Auto-populate commission from customer's rep assignments. Per-line calculation, aggregated to header. Respects manual overrides (override=True lines skipped). |
| `accrue_commission` | `(transaction_id: int, model_name: str, ida_prefix: str) -> dict` | Create GL entries: Commission Expense debit / Commission Payable credit per rep. |

**Manage actions:** `populate_commission`, `accrue_commission`

**Three calculation methods:**
- **revenue** (default): `rate_pct * level_factor * split_pct * extended_price`
- **margin**: `rate_pct * level_factor * split_pct * (extended_price - extended_cost)`
- **script**: placeholder for stored scripts (falls back to revenue)

**Price level factors** (wc2 insight -- margins differ by level, so commissions should too):
- retail: 1.0, wholesale: 0.7, distributor: 0.5, employee: 0.0, cost: 0.0

**GL accounts written:**
- Debit: Commission Expense (resolution chain below)
- Credit: Commission Payable (resolution chain below)

**GL resolution chain:** `invoice.commission.gl` -> `rep.gl_accounts` -> `Setting('commission_config').data.gl_accounts` -> `Setting('gl_account_defaults').data` -> hardcoded (`EXP-COMMISSIONS-000` / `LIAB-COMMPAY-000`)

**Dependencies:** Called by `journalize_invoice` after invoice posting. Uses `_get_setting_gl()` to walk Setting records for GL account resolution.

---

### credit_check.py

**File:** `apps/transactions/services/credit_check.py`
**Purpose:** Credit limit warnings (never barriers) with audit trail.

| Function | Signature | Description |
|----------|-----------|-------------|
| `check_credit_limit` | `(customer_id: int, new_amount: float = 0, exclude_order_id: int = None) -> dict` | Check exposure (balance_due + open_orders + new_amount) against limit. Returns warning flag, amounts, message. Never blocks. |
| `acknowledge_credit_override` | `(transaction_id: int, model_name: str, contact_id: int, reason: str) -> dict` | Store override acknowledgement in `transaction.metadata.credit_warnings[]`. Audit trail. |
| `check_bad_check_history` | `(customer_id: int) -> dict` | Check for bounced/returned payments in financial.customer.complaints and Payment records. |
| `get_credit_warnings_for_transaction` | `(transaction_id: int, model_name: str) -> list[dict]` | Read credit warning audit trail from transaction metadata. |

**Exposure formula (WC2 RunningBalance rule):**
```
total_exposure = AR balance_due + open_order_backlog + current_document_amount
```
Open order backlog = sum of `Order.total` where status is not `complete` or `canceled`. Without including open orders, a customer with $50K in open orders could place another $50K against a $60K credit limit. The `exclude_order_id` parameter prevents double-counting when the current order is being edited (its total is already represented by `new_amount`).

**Warning message breakdown:** When triggered, the message shows the components: `AR $X + open orders $Y + this document $Z exceeds limit $L by $O`.

**Return dict:** `{warning, limit, balance_due, open_orders, new_amount, total_exposure, amount_over, message}`

**Manage actions:** `check_credit_limit`, `acknowledge_credit_override`

**Settings/Config:** Credit limit from `OrgBase.financial.customer.credit.limit`. Balance due from `OrgBase.financial.customer.balances.due`. Bad check history from `financial.customer.complaints` and Payment status fields.

**GL accounts:** None -- advisory only.

---

### payment_pending.py

**File:** `apps/transactions/services/payment_pending.py`
**Purpose:** One-path payment application through PendingPaymentApplication records.

| Function | Signature | Description |
|----------|-----------|-------------|
| `apply_payment_to_invoice` | `(payment_id, invoice_id, amount, reason, contact_id) -> dict` | Create PendingPaymentApplication. If invoice unlocked, apply immediately (update totals, set status). If locked, queue. |
| `apply_pending_for_invoice` | `(invoice_id: int) -> dict` | Apply all pending payments for an invoice after unlock. Processes in dt_created order. |
| `get_pending_for_invoice` | `(invoice_id: int) -> dict` | List all pending payment applications for an invoice. |

**Manage actions:** `apply_payment_to_invoice`, `apply_pending_payments`

**GL accounts:** None directly -- journalization handles GL posting separately.

---

### sales_pipeline.py

**File:** `apps/transactions/services/sales_pipeline.py`
**Purpose:** Connect selling actions to future outcomes. Funnel: Actions → Proposals → Orders → Revenue.

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_sales_pipeline` | `(year, month, months, customer_id) -> dict` | Full funnel with conversion rates, impact analysis, breakdown by action type and rep. |

**Funnel stages:** Actions (with `action_type` + `predicted_impact`) → Proposals → Orders (via `parent_model='proposal'`) → Invoices (via `parent_model='order'`).

**Impact analysis:** Groups actions by `predicted_impact` level (1-5), traces forward to see which contacts produced proposals/orders. Compares prediction accuracy: high-impact predictions that produce orders = good calibration; high-impact predictions with no outcome = over-optimism.

**Action model fields (added 2026-08-11):**
- `action_type` — CharField, choices: call, email, visit, meeting, demo, marketing, referral, social, event, follow_up, other
- `impact` — JSONField. Not precision, but retrospection. Schema:
  ```json
  {
    "predicted": 4,     // waffly 1-5 gut feel at time of action
    "actual": 2,        // waffly 1-5 looking back at what happened
    "refs": {
      "transactions": [{"model": "order", "id": 1234, "ida": "SO-1234", "value": 450.00}],
      "explanation": "Customer was comparison shopping — enthusiasm ≠ commitment"
    }
  }
  ```
  The gap between predicted and actual is the learning signal. Alice and users both contribute to defining actual.

**Manage action:** `get_sales_pipeline`

**Dashboard:** `/sales-pipeline` — funnel bars, conversion rates, action type breakdown, predicted vs. actual calibration card.

---

### cash_conversion.py

**File:** `apps/accounts/services/cash_conversion.py`
**Purpose:** Measure the cash conversion cycle — where money stalls. Dashboard: `/cash-conversion`.

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_cash_conversion` | `(year, month) -> dict` | Four-stage pipeline: Order→Invoice (fulfillment), Invoice→Payment (collection), Payment→GL (posting), GL→Period Close (reconciliation). Returns avg/median days per stage, stalled records with dollar values, alerts for >30 day stalls. |

**Manage action:** `get_cash_conversion`

---

### inventory_velocity.py

**File:** `apps/products/services/inventory_velocity.py`
**Purpose:** Where capital is working vs parked. Dashboard: `/inventory-velocity`.

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_inventory_velocity` | `(year, month, category) -> dict` | Five views: PO exposure by vendor, receipt performance (avg days + on-time %), on-hand ABC analysis with margin velocity, sales turns by category, reorder alerts with days-of-supply. |

**Manage action:** `get_inventory_velocity`

---

### inventory_flight_sim.py

**File:** `apps/products/services/inventory_flight_sim.py`
**Purpose:** Flight Simulator: Inventory — interactive training for inventory and GL flows. Dashboard: `/flight-sim-inventory`.

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_item_flight_state` | `(item_id: int) -> dict` | Live state of an item: all transaction lines, pending records, GL impact per line (including 5% tax, 5% commission). |
| `get_flight_scenario` | `() -> dict` | Scripted 9-step training scenario with expected values at each step. |

**Training scenario (9 steps):**
1. Starting inventory (on_hand=100)
2. Proposal for 15 → on_p changes, no GL
3. Convert 9 to Order → on_so changes, pending created, no GL
4. Invoice 4 → on_hand decreases, GL: AR/Revenue/Tax/COGS/Inventory/Commission
5. Purchase 14 → on_po increases, no GL
6. Receive 11 → on_hand increases, GL: Inventory/AP
7. Partial payment $30 of $42 → GL: Cash/AR
8. Discount $10 → GL: Discount Expense/AR
9. Write-off $2 → GL: Bad Debt/AR

**Invoice settlement summary:** $42 = $30 cash + $10 discount + $2 write-off. Margin waterfall: Revenue $40 → COGS $24 = Gross $16 → Commission $2 → Discount $10 → Bad Debt $2 = Net $2 (5%).

**Config:** Tax 5%, Commission 5% (easy mental math for learners).

**Manage actions:** `get_item_flight_state`, `get_flight_scenario`

---

### campaign_roi.py

**File:** `apps/transactions/services/campaign_roi.py`
**Purpose:** Campaign ROI tracking, customer acquisition cost, margin velocity.

| Function | Signature | Description |
|----------|-----------|-------------|
| `create_campaign` | `(name, budget, channel, start_date, end_date, description) -> dict` | Create campaign as a Setting record (purpose='campaign'). |
| `record_campaign_spend` | `(campaign_id: int, amount: Decimal, description) -> dict` | Record spending against a campaign. |
| `calculate_campaign_roi` | `(campaign_id: int) -> dict` | Count linked transactions, sum revenue, compute ROI = (revenue - spent) / spent * 100. |
| `get_all_campaigns` | `() -> list[dict]` | All campaigns with current metrics. |
| `link_transaction_to_campaign` | `(model_name, record_id, campaign_id) -> dict` | Set source.campaign_id on a transaction. |
| `attribute_customer_to_campaign` | `(customer_id, campaign_id) -> dict` | First-touch attribution via customer.refs.links.campaigns. |
| `get_campaign_cac` | `(campaign_id: int) -> dict` | CAC = spend / attributed customer count. Uses PostgreSQL jsonb containment query. |
| `get_campaign_margin_velocity` | `(campaign_id: int) -> dict` | margin * turns for campaign-linked invoices. |

**Manage actions:** `create_campaign`, `record_campaign_spend`, `calculate_campaign_roi`, `get_all_campaigns`, `link_transaction_to_campaign`, `attribute_customer_campaign`, `get_campaign_cac`, `get_campaign_margin_velocity`

**Settings/Config:** Campaigns stored as Setting records with `purpose='campaign'`. Transaction linkage via `source.campaign_id` JSON field on headers.

**GL accounts:** None -- reporting only.

---

### order_production.py

**File:** `apps/transactions/services/order_production.py`
**Purpose:** Order fulfillment workflow: Order -> Work Orders -> Ship -> Invoice.

| Function | Signature | Description |
|----------|-----------|-------------|
| `spawn_work_order` | `(order_id: int) -> dict` | Create WorkOrder + WorkOrderLines from order. Links via order.flow.children. |
| `record_production_action` | `(order_id, action_text, assigned_to) -> dict` | Create Action record for production tracking. |
| `partial_ship` | `(order_id, shipped_lines: list[dict]) -> dict` | Ship selected lines, create invoice for shipped qty, create backorder for remainder. Updates order status. |
| `complete_order` | `(order_id: int) -> dict` | Close order (set status='complete'). |

**Manage actions:** `spawn_work_order`, `record_production_action`, `partial_ship`, `complete_order`

**Dependencies:** Calls `adjust_item_quantity()` from inventory_pending for on_hand decrements (one-path). Calls `create_backorder_entries()` from backorder service for remainders.

**GL accounts:** None directly -- invoice journalization handles GL.

---

## Products

### inventory_pending.py

**File:** `apps/products/services/inventory_pending.py`
**Purpose:** ONE PATH for all item.quantity changes through PendingInventoryAdjustment records.

| Function | Signature | Description |
|----------|-----------|-------------|
| `adjust_item_quantity` | `(item_id, field, delta, reason, source_type, source_id, source_line_id, inventory_layer_id) -> dict` | Create pending adjustment, apply immediately if item unlocked. The ONLY function that writes item.quantity. |
| `apply_pending_for_item` | `(item_id: int) -> dict` | Apply all pending adjustments after item unlock. |
| `get_pending_for_item` | `(item_id: int) -> list` | List all pending adjustments for an item. |

**Manage actions:** Called internally by `order_production.partial_ship` and other services. No direct manage action (inventory changes must flow through a business event, not raw adjustment).

**Settings/Config:** Uses InventoryLayer model. Creates placeholder layer (source_doc_type='system') for non-layer adjustments (on_p, on_so).

**GL accounts:** None -- journalization handles GL posting for the parent transaction.

---

### suggest_purchase.py

**File:** `apps/products/services/suggest_purchase.py`
**Purpose:** Reorder automation with preferred vendor resolution.

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_preferred_vendor` | `(item_id: int) -> dict` | Resolve preferred vendor: item.vendor_id -> ItemXRef(is_preferred, source='wholesaler') -> first OrgItem(org_type='vendor'). |
| `get_items_below_reorder` | `(warehouse_id: int = None) -> list[dict]` | Find items where on_hand or available < OrgItem.quantity_minimum. |
| `suggest_purchase_orders` | `(warehouse_id: int = None) -> list[dict]` | Group below-reorder items by preferred vendor into suggested POs with estimated totals. |
| `create_draft_purchase` | `(vendor_id, items: list[dict]) -> dict` | Create actual Purchase record (status='planned') with PurchaseLines. |

**Manage actions:** `get_items_below_reorder`, `suggest_purchase_orders`, `create_draft_purchase`

**Settings/Config:** Reorder point from `OrgItem.quantity_minimum`. Reorder max from `OrgItem.quantity_maximum`. Item quantities from `Item.quantity` JSONB.

**GL accounts:** None -- purchase journalization handles GL after receipt.

---

### map_enforcement.py

**File:** `apps/products/services/map_enforcement.py`
**Purpose:** Minimum Advertised Price enforcement -- checks sell prices against MAP/MSRP.

| Function | Signature | Description |
|----------|-----------|-------------|
| `check_map_violation` | `(item_id: int, sell_price) -> dict` | Check single item: sell_price < MAP? MAP source: item.price.msrp -> ItemXRef(source='manufacturer') cost.map_price/msrp. |
| `check_order_map_violations` | `(order_id: int) -> list[dict]` | Check all order lines for MAP violations. |
| `get_map_violations_report` | `(period_days: int = 30) -> list[dict]` | Scan recent invoices for MAP violations. Returns invoice/item/customer/price details. |

**Manage actions:** `check_map_violation`, `check_order_map_violations`, `get_map_violations_report`

**GL accounts:** None -- reporting only.

---

### pricing.py

**File:** `apps/products/services/pricing.py`
**Purpose:** Price level resolution for order/invoice lines.

| Function | Signature | Description |
|----------|-----------|-------------|
| `resolve_price_level` | `(customer_level, header_level, line_level) -> str` | Determine effective level: line > header > customer > 'base'. |
| `resolve_unit_price` | `(item_price: dict, price_level: str, quantity: float) -> Decimal` | Resolve unit price at level with quantity break lookup. Falls back: level -> base -> 0. |
| `get_price_for_line` | `(item, customer, header_price_level, line_price_level, quantity) -> dict` | Full price resolution for a line. Returns resolved_level, unit_price, extended, and the chain for transparency. |

**Manage actions:** None (called internally by other services and wcapi line-save logic).

**Valid price levels:** base, msrp, retail, wholesale, distributor, sample

**Settings/Config:** Prices from `Item.price` JSONB dict. Quantity breaks from `Item.price.qty_breaks[]` (sorted by min_qty ascending).

---

## Organizations

### vendor_scorecard.py

**File:** `apps/orgs/services/vendor_scorecard.py`
**Purpose:** Compute vendor performance from PO vs Receipt data.

| Function | Signature | Description |
|----------|-----------|-------------|
| `compute_vendor_scorecard` | `(vendor_id: int, period_days: int = 90) -> dict` | Compute all four metrics + weighted overall. |
| `update_vendor_scorecard` | `(vendor_id: int) -> dict` | Compute and persist scorecard in `vendor.financial.vendor.scorecard`. |
| `get_all_vendor_scores` | `() -> list[dict]` | All vendors with scorecards, sorted by overall_score desc. Computes live if no stored scorecard. |

**Manage actions:** `compute_vendor_scorecard`, `update_vendor_scorecard`, `get_all_vendor_scores`

**Metrics and weights:**
| Metric | Weight | Source |
|--------|--------|--------|
| On-time delivery % | 40% | Receipt dt_received vs PO dt_created + lead_time_days |
| Fill rate % | 30% | qty received / qty ordered (capped at 100%) |
| Quality score | 20% | Complaints in vendor.financial.vendor.complaints (linear 0-100, cap at 20 complaints) |
| Pricing accuracy % | 10% | PO cost vs receipt cost variance |

**Settings/Config:** Lead time from `vendor.financial.manufacturer.lead_time_days` (default 14). Complaints from `vendor.financial.vendor.complaints`.

---

### rebate_accrual.py

**File:** `apps/orgs/services/rebate_accrual.py`
**Purpose:** Manufacturer rebate accrual based on purchase volume.

| Function | Signature | Description |
|----------|-----------|-------------|
| `accrue_manufacturer_rebate` | `(manufacturer_id, period_start_ms, period_end_ms) -> dict` | Calculate rebate = purchases * rate / 100. Updates financial.manufacturer.rebates. Creates GL entries. |
| `get_rebate_summary` | `() -> list[dict]` | All manufacturers with rebate activity (rate > 0 or earned > 0 or pending > 0). |

**Manage actions:** `accrue_manufacturer_rebate`, `get_rebate_summary`

**Settings/Config:** Rebate rate from `manufacturer.prefs.rebate_rate_pct`. Tracking in `manufacturer.financial.manufacturer.rebates` (earned_ytd, received_ytd, pending).

**GL accounts written:**
- Debit: `ASSET-AR-000` (Rebate Receivable)
- Credit: `REV-MISC-000` (Rebate Income)

---

## Cross-Cutting Patterns

### The One Path Pattern

**Principle:** Every inventory change and every payment application flows through a pending record first. No direct writes to `item.quantity` or `invoice.totals`.

**PendingInventoryAdjustment** (`inventory_pending.py`):
1. Caller requests a quantity change via `adjust_item_quantity(item_id, field, delta, reason, ...)`
2. A `PendingInventoryAdjustment` record is always created (state='pending')
3. If the item is unlocked, the adjustment applies immediately:
   - item.quantity[field] += delta
   - item.quantity.available recalculated
   - pending.state set to 'applied'
4. If the item is locked, the record stays pending
5. When the item is later unlocked, `apply_pending_for_item(item_id)` processes the queue in order

**PendingPaymentApplication** (`payment_pending.py`):
1. Caller requests payment application via `apply_payment_to_invoice(payment_id, invoice_id, amount, ...)`
2. A `PendingPaymentApplication` record is always created (state='pending')
3. If the invoice is unlocked, the payment applies immediately:
   - invoice.totals.received += amount
   - invoice.totals.balance recalculated
   - invoice.status updated (paid / partially_paid)
   - pending.state set to 'applied'
4. If the invoice is locked (e.g., during journalization), the record stays pending
5. When unlocked, `apply_pending_for_invoice(invoice_id)` processes pending payments in chronological order

**Why One Path matters:**
- Single audit trail -- every change has a pending record with reason, source, and timestamp
- Locking is safe -- journalization locks invoices/items, and pending records queue automatically
- No race conditions -- `select_for_update()` on the target record inside atomic transactions
- Debugging is simple -- `get_pending_for_item()` / `get_pending_for_invoice()` shows the full history

---

### GL Resolution Chains

**Invoice journalization:**
```
Revenue account: customer GL override -> item.gls.revenue -> 'REV-SALES-000'
AR account:      customer GL override -> 'ASSET-AR-000'
COGS account:    item.gls.cogs -> 'COGS-PRODUCTS-000'
Inventory:       item.gls.inventory -> 'ASSET-INVENTORY-000'
```

**Commission accrual:**
```
Expense account:  invoice.commission.gl.expense
                  -> rep.gl_accounts.commission_expense
                  -> Setting('commission_config').data.gl_accounts.expense
                  -> Setting('gl_account_defaults').data.commission_expense
                  -> 'EXP-COMMISSIONS-000'

Payable account:  invoice.commission.gl.payable
                  -> rep.gl_accounts.commission_payable
                  -> Setting('commission_config').data.gl_accounts.payable
                  -> Setting('gl_account_defaults').data.commission_payable
                  -> 'LIAB-COMMPAY-000'
```

**Price level resolution:**
```
line.price_level (user override)
  -> header.price_level (inherited from customer at order creation)
  -> customer.price_level (org default)
  -> 'base' (system fallback)
```

Within the resolved level, quantity breaks from `item.price.qty_breaks[]` apply if defined (highest qualifying break wins).

---

### Manage Action Quick Reference

| Action | Service | Required params |
|--------|---------|----------------|
| `journalize_invoice` | journalize | `invoice_id` |
| `journalize_payment` | journalize | `payment_id` |
| `journalize_purchase` | journalize | `purchase_id` |
| `batch_journalize` | journalize | (optional `ida_prefix`) |
| `populate_commission` | commission | `transaction_id`, `model_name` |
| `accrue_commission` | commission | `transaction_id`, `model_name` |
| `check_credit_limit` | credit_check | `customer_id` (optional `new_amount`) |
| `acknowledge_credit_override` | credit_check | `transaction_id`, `model_name`, `contact_id` |
| `apply_payment_to_invoice` | payment_pending | `payment_id`, `invoice_id`, `amount` |
| `apply_pending_payments` | payment_pending | `invoice_id` |
| `spawn_work_order` | order_production | `order_id` |
| `record_production_action` | order_production | `order_id`, `action_text` |
| `partial_ship` | order_production | `order_id`, `shipped_lines` |
| `complete_order` | order_production | `order_id` |
| `get_items_below_reorder` | suggest_purchase | (optional `warehouse_id`) |
| `suggest_purchase_orders` | suggest_purchase | (optional `warehouse_id`) |
| `create_draft_purchase` | suggest_purchase | `vendor_id`, `items` |
| `check_map_violation` | map_enforcement | `item_id`, `sell_price` |
| `check_order_map_violations` | map_enforcement | `order_id` |
| `get_map_violations_report` | map_enforcement | (optional `period_days`) |
| `compute_vendor_scorecard` | vendor_scorecard | `vendor_id` (optional `period_days`) |
| `update_vendor_scorecard` | vendor_scorecard | `vendor_id` |
| `get_all_vendor_scores` | vendor_scorecard | (none) |
| `accrue_manufacturer_rebate` | rebate_accrual | `manufacturer_id` |
| `get_rebate_summary` | rebate_accrual | (none) |
| `create_campaign` | campaign_roi | `name` (optional `budget`, `channel`) |
| `record_campaign_spend` | campaign_roi | `campaign_id`, `amount` |
| `calculate_campaign_roi` | campaign_roi | `campaign_id` |
| `get_all_campaigns` | campaign_roi | (none) |
| `link_transaction_to_campaign` | campaign_roi | `model_name`, `record_id`, `campaign_id` |
| `attribute_customer_campaign` | campaign_roi | `customer_id`, `campaign_id` |
| `get_campaign_cac` | campaign_roi | `campaign_id` |
| `get_campaign_margin_velocity` | campaign_roi | `campaign_id` |
| `log_user_navigation` | user_patterns | `contact_id`, `entries` |
| `analyze_user_patterns` | user_patterns | `contact_id` |
| `get_all_user_patterns` | user_patterns | (none) |
| `log_user_search` | user_patterns | `contact_id`, `model`, `search_term` |
| `analyze_search_patterns` | user_patterns | (none) |
| `promote_search_preset` | user_patterns | `model`, `term` |
| `save_alice_observation` | user_patterns | `contact_id`, `observation` |

---

## AI / Coaching

### user_patterns.py
**Path:** `apps/ai_assistant/services/user_patterns.py`
**Purpose:** Track how users actually work, detect patterns, suggest improvements. The builder story: don't design sidewalks — watch where people walk, then pave those paths.

**Behavior Lifecycle:**
```
Observed (dt stamped) → Frequent (pattern detected) → Suggested (Alice recommends)
    ↓                                                        ↓
Pruned (unused 90 days)                              Promoted (user accepts → Setting)
                                                           ↓
                                                   Permanent (survives pruning)
```

Quarterly and yearly patterns are preserved — a search someone runs every January is not pruned in March.

**Functions:**

| Function | What it does |
|----------|-------------|
| `log_user_navigation(contact_id, entries)` | Buffer model-view events from frontend (batched every 30s) |
| `log_user_search(contact_id, model, search_term, result_count)` | Record searches with result counts |
| `analyze_user_patterns(contact_id)` | Detect frequent sequences, top models, suggest dashboards |
| `analyze_search_patterns()` | Find searches used by 2+ users — preset candidates |
| `promote_search_preset(model, term, label)` | Pave the path — create shared preset in Setting |
| `infer_frequency(timestamps)` | Classify usage as daily/weekly/monthly/quarterly/yearly |
| `prune_user_metadata(contact_id, max_age_days)` | Prune old entries, preserve periodic patterns, flag promotion candidates |
| `save_alice_observation(contact_id, observation, category)` | Store coaching observation on contact |
| `get_all_user_patterns()` | Batch analysis of all users for Alice's 4-hour cron |

**Data stored in contact.metadata:**

| Key | Cap | Pruned after | Promoted? |
|-----|-----|-------------|-----------|
| `navigation_log` | 500 entries | 90 days | No (patterns extracted, raw data drops) |
| `search_log` | 200 entries | 90 days (unless periodic) | Yes → `search_presets` Setting |
| `alice_observations` | 50 entries | 30 days after acknowledged | No |
| `databrowser` | 1 dict | Never | N/A — user preferences |

**Settings:**

| Setting name | What it holds |
|-------------|---------------|
| `search_presets` | Promoted searches visible to all users. `data.presets[]` with model, term, label, dt_promoted |

**Scheduled:** `alice-patterns.py` runs every 4 hours, calls `get_all_user_patterns()` and `analyze_search_patterns()`, posts observations and promotion candidates.
