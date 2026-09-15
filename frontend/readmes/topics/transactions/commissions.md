# Commissions — WebClerk 3.0

Established 2026-08-05.

## Architecture

Commission mirrors the tax pattern: backend service calculates, frontend displays
and allows per-line override. The backend service (`commission.py`) is complete.
The frontend wiring was added 2026-08-05.

### The WC2 Pattern (Preserved)

```
Rep record
  └── rate_pct (e.g., 10%)

Item price_level
  └── level_factor (retail=100%, wholesale=80%, distributor=50%, employee=0%)

Effective rate = rate_pct × level_factor × split_pct
Commission     = base_amount × effective_rate
```

Three calculation bases:
- **revenue** — commission on selling price (default)
- **margin** — commission on (sell price - cost)
- **script** — stored script from rep record (future)

### Data Flow

```
Customer record
  └── refs.links.reps[] → rep assignments (1 or more)

Rep record (OrgBase with type='rep')
  └── financial.rep.commissions.rate_pct → base rate
  └── prefs.commission.basis → revenue | margin | script
  └── prefs.commission.level_factors → {retail: 1.0, wholesale: 0.7, ...}

Transaction header
  └── commission JSONField → {reps[], total, basis, accrued, dt_accrued}
  └── price_level → selects level_factor

Transaction line
  └── commission JSONField → same structure, per-line
```

### Salesperson vs Rep

Both are entries in the `commission.reps[]` array. A transaction can have:
- One salesperson (internal employee) with their rate
- One or more reps (external) with their rates
- Split commissions — `split_pct` divides automatically when multiple reps

The backend `populate_transaction_commission()` auto-splits evenly across all
reps assigned to the customer. Users override at the line level.

---

## Backend Service

**File:** `apps/transactions/services/commission.py`

| Function | What it does |
|----------|-------------|
| `calculate_line_commission()` | One line: price_ext, cost_ext, price_level, rep_configs → commission object |
| `populate_transaction_commission()` | Auto-populate: customer → reps → per-line calc → header aggregate |
| `accrue_commission()` | GL entries on invoice journalize: Expense debit / Payable credit |
| `get_rep_commission_config()` | Load rate, basis, level_factors from rep's OrgBase record |
| `get_customer_rep_ids()` | Get rep IDs from customer's `refs.links.reps` |
| `empty_commission()` | Schema for header/line commission object |
| `empty_rep_entry()` | Schema for one rep's commission entry |

### Commission Object Schema

```json
{
  "reps": [
    {
      "rep_id": 42,
      "rep_ida": "JSmith",
      "name": "John Smith",
      "rate_pct": 10.0,
      "split_pct": 100.0,
      "level_factor": 0.7,
      "effective_rate": 7.0,
      "basis": "revenue",
      "amount": 139.97,
      "override": false,
      "override_reason": ""
    }
  ],
  "total": 139.97,
  "basis": "revenue",
  "accrued": false,
  "dt_accrued": 0
}
```

### Override Protection

`populate_transaction_commission()` skips lines where any rep has `override: true`.
This means users can adjust individual lines and re-run the auto-populate without
losing their manual changes.

### GL Accrual

On invoice journalize, `accrue_commission()` creates:
- Debit: Commission Expense (per rep)
- Credit: Commission Payable (per rep)

GL resolution chain: `invoice.commission.gl` → `rep.gl_accounts` →
`commission_config` Setting → `gl_account_defaults` Setting → hardcoded defaults.

---

## Frontend Components

### Hidden by Default

Commission columns and footer display are **hidden** unless the user clicks the
**C** button in the line card panel buttons (alongside L, S, XR, M).

### Columns (sell-side only, visible when C is toggled on)

| Column | Field | Width | Editable | Description |
|--------|-------|-------|----------|-------------|
| `comm%` | `comm_rate` | 55px | Yes (bulk) | Rep's base rate_pct |
| `eff%` | `comm_eff_rate` | 55px | Calculated | rate × level_factor × split |
| `comm$` | `comm_total` | 80px | Calculated | Commission amount for the line |

### Footer

When C is toggled on, the footer shows `Comm: $X,XXX.XX` in purple between
the Other and Deposit totals. Uses header `commission.total` if available,
otherwise sums from line records.

### Field Update (comm_rate edit)

When user edits `comm%` on a line:
1. Reads existing `commission.reps[0]` for level_factor, split_pct, basis
2. Calculates: `base_amount × (newRate / 100) × level_factor × (split_pct / 100)`
3. Sets `override: true`, `override_reason: 'manual'` on the rep entry
4. Recalculates line total from all reps
5. Marks line `_dirty` for backend save

Bulk edit via header click applies the same rate to all selected lines.

### Toggle Button

The **C** button in the footer bar panel buttons row:
- Purple when active, slate when inactive
- Toggles `showCommission` state in useLineCard
- Controls column visibility, footer commission display, and CommissionPanel
- Sell-side only (no commission on purchase/receipt lines)

### Commission Panel

`CommissionPanel.tsx` appears below the grid when C is toggled on:
- **Rep summary cards** at top — name, rate, split, effective rate, amount, basis, override flag
- **Per-line table** — item, description, extended, rep(s), rate, eff%, commission
- **Selection-aware totals** — sales, commission, effective % (same pattern as MarginPanel)

### Populate Trigger

When a customer is selected on a sell-side transaction:
1. `applyCustomerDefaults` checks `refs.links.reps` and `relations.rep_ids`
2. If reps found, sets `has_reps: true` on the defaults
3. Toast shows "(commission will populate on save)"
4. On save, `handleSave` calls `populateCommission(modelName, txId)`
5. Backend `populate_transaction_commission` calculates per line, aggregates to header
6. Toast confirms rep names

### Commission Reports

Commission reports are accessed from the **rep** and **employee** models (not from
transactions). All commission reports require `role_required: 'admin'`.

**Two report modes** (`CommissionReportPrintDocument.tsx`):

| Mode | Triggered by | What it shows |
|------|-------------|---------------|
| **Company Summary** | Rep model → "Commission Summary" | All reps: name, basis, rate, invoices, sales credited, commission earned, accrued/paid/pending. Approval section. |
| **Individual Statement** | Rep model → "Commission Statement" | One rep: invoice-by-invoice detail (invoice #, date, customer, sale amount, credited, rate, effective rate, commission, accrued status). Summary boxes for earned/accrued/paid/pending. Approval section. |

**Report entries in `reportLists.ts`:**

| Model | Report | Description |
|-------|--------|-------------|
| **rep** | Commission Statement | Individual rep statement with invoice detail |
| **rep** | Commission Summary | All reps summary for period |
| **rep** | Sales Credited by Rep | Sales credited with customer breakdown |
| **employee** | Employee Commission Statement | Same as rep statement for employees with commissions |

**Backend data service:** `get_commission_report(period_start, period_end, rep_id=None)`

- Queries invoices in the date range that have commission data
- Aggregates by rep: sales credited, commission earned, invoice count, accrued/paid/pending
- When `rep_id` is set, returns invoice-level detail for that rep
- Wired to manage_view as `get_commission_report` action (staff-only)

**Data flow:** User opens rep record → Reports dialog → picks report → date range
prompt → calls `get_commission_report` → renders `CommissionReportPrintDocument`
→ `window.print()`.

### Security — Commission Data Is Internal-Only

Commission data is gated at every layer. Added 2026-08-05.

**Backend:**
- `_STAFF_ONLY_ACTIONS` in manage_view gates `populate_commission`, `accrue_commission`, `get_commission_report` — returns 403 for non-staff
- `_require_staff()` check on all 3 ViewSet `populate_commission` actions
- `RoleAwareModelSerializer.to_representation()` strips `commissions`, `commission_total`, `commission_rate` from `cost`/`finance`/`commission` JSON envelopes for non-staff
- Bootstrap view returns empty `commissions` config for non-staff
- Auth endpoints now return `is_staff` and `is_superuser` (login + /me)

**Frontend:**
- `User` interface has `is_staff` and `is_superuser` fields
- C toggle button hidden for non-staff (`LineCardRenderer.tsx`)
- Commission footer totals hidden for non-staff
- Commission row in TabsRenderer totals hidden for non-staff
- `cost.commissions` in SummaryCard hidden for non-staff
- Auto-populate commission call + toast gated to staff only (`TransactionDetail.tsx`)
- Rep commission section in OrgFinancialsPanel hidden for non-staff
- Employee commission section removed (was in EmployeeTab)
- All commission reports require `role_required: 'admin'` in reportLists

### Backend Endpoints

| Endpoint | Method | What it does | Staff only |
|----------|--------|-------------|------------|
| `/tx/proposals/{id}/populate_commission/` | POST | Populate commission from customer's reps | Yes |
| `/tx/orders/{id}/populate_commission/` | POST | Same for orders | Yes |
| `/tx/invoices/{id}/populate_commission/` | POST | Same for invoices | Yes |
| `/wcapi/manage/` `get_commission_report` | POST | Report data for date range ± rep_id | Yes |
| `/wcapi/manage/` `populate_commission` | POST | Same as ViewSet action via manage | Yes |
| `/wcapi/manage/` `accrue_commission` | POST | GL accrual entries | Yes |

---

## Remaining Work

### Already Done
- [x] Backend commission service (calculate, populate, accrue, GL)
- [x] Commission JSONField on all transaction headers and lines (migration 0008)
- [x] Rep financial structure (rate_pct, mtd, ytd, lifetime, pending, paid)
- [x] RepTab in OrgFinancialsPanel (displays commission data)
- [x] LineCardRenderer reads commission_rate from items on add
- [x] Commission columns in useLineCard (hidden by default, C toggle)
- [x] Per-line comm_rate editing with override protection
- [x] Commission total in footer (hidden unless C toggled on)
- [x] Bulk edit comm_rate via header click
- [x] **Populate trigger** — `applyCustomerDefaults` detects `has_reps` flag. After save, `handleSave` calls `populateCommission()` endpoint. Toast confirms rep names. ViewSet actions on Proposal, Order, Invoice. 2026-08-05.
- [x] **Commission panel** — `CommissionPanel.tsx` shows below grid when C toggled on. Rep summary cards (rate, split, eff%, amount, basis, override flag). Per-line table. Selection-aware totals. 2026-08-05.
- [x] **Commission report** — Two modes: company summary + individual rep statement. Backend `get_commission_report` data service. Report entries on rep and employee models. 2026-08-05.
- [x] **Security** — Staff-only gate on all commission endpoints, serializer stripping, frontend hiding, report role gating. 2026-08-05.

### To Do
- [ ] **Script basis** — execute stored scripts from rep records for custom commission calculations.
- [ ] **Commission payment** — pay accrued commissions, create payment records, update rep financial totals.

---

## Default Level Factors

| Price Level | Factor | Meaning |
|------------|--------|---------|
| retail | 1.00 | Full commission |
| wholesale | 0.70 | 70% of base rate |
| distributor | 0.50 | 50% of base rate |
| employee | 0.00 | No commission |
| cost | 0.00 | No commission |

Custom level factors can be set per rep in `prefs.commission.level_factors`.
