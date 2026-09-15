# Collections — Customer Health, Statements, and Past-Due Management

## Overview

WebClerk tracks customer fiscal health in `financial.customer` on every OrgBase
record. The collections workflow uses these fields to automate statement sending,
surface past-due accounts, and measure payment behavior over time.

## Customer Financial Structure

### `financial.customer.collection` (per customer)

| Field | Type | Purpose |
|-------|------|---------|
| `dt_last_statement` | datetime | When last statement was sent — batch sender checks this |
| `dt_last_contact` | datetime | When last collection call/email was made |
| `health_score` | green/yellow/red | Fiscal health — maintained by nightly maintenance |
| `velocity_trend` | improving/stable/deteriorating | Payment speed direction |
| `cost_mtd` | float | Collection costs month-to-date |
| `cost_ytd` | float | Collection costs year-to-date |
| `cost_alltime` | float | Lifetime collection costs |

### `financial.customer.payment` (per customer)

| Field | Type | Purpose |
|-------|------|---------|
| `days_avg_paid` | int | Average days from invoice to payment |
| `days_pay` | int | Current terms in days |
| `dt_last_payment` | datetime | Most recent payment date |
| `last_payment_amount` | float | Most recent payment amount |

### `financial.customer.aging` (per customer)

| Field | Type | Purpose |
|-------|------|---------|
| `future` | float | Not yet due |
| `period_1` | float | 1-30 days past due |
| `period_2` | float | 31-60 days past due |
| `period_3` | float | 61-90+ days past due |

### `financial.common.settings` (per customer)

| Field | Default | Purpose |
|-------|---------|---------|
| `statement_interval_days` | 30 | Minimum days between statement sends |
| `discount_pct` | 0 | Early-payment discount percentage |
| `tax_exempt` | false | Tax exemption flag |
| `terms_id` | null | FK to terms record |

## Health Score Calculation

Maintained by nightly financial maintenance job. Thresholds:

| Score | Condition |
|-------|-----------|
| **Red** | `aging.period_3 > 0` (61+ days past due) OR `payment.days_avg_paid > 45` |
| **Yellow** | Any past due (`period_1 + period_2 > 0`) OR `payment.days_avg_paid > 30` |
| **Green** | Current, velocity under 30 days |

## Velocity Trend

Compares average payment speed of last 5 payments vs prior 5 payments:

| Trend | Condition |
|-------|-----------|
| **Improving** | Recent avg is 3+ days faster than prior |
| **Stable** | Within 3-day band |
| **Deteriorating** | Recent avg is 3+ days slower than prior |

## Batch Statement Flow

1. User opens Accounting Dashboard → Collections section
2. Selects past-due customers (or "Select All Past Due")
3. Clicks "Send Statements"
4. For each customer:
   - Check `today - dt_last_statement >= statement_interval_days`
   - **Skip** if within interval (already received a recent statement)
   - **Send** if past interval — uses Statement report with conditional dunning message
   - Update `dt_last_statement` after send
5. Alice tracks sent/skipped counts, flags customers with no improvement after 3 statements

## Conditional Dunning Messages

The Statement report (id=409) uses a `conditional_text` section that selects
the appropriate message based on the customer's aging:

| Aging Bucket | Message Tone |
|-------------|--------------|
| Current | "Thank you for your continued business and prompt payment." |
| 1-30 days | "Your account is past due. Please remit payment at your earliest convenience." |
| 31-60 days | "Your account is seriously past due. Please contact us immediately to arrange payment." |
| 61+ days | "FINAL NOTICE: Your account is over 90 days past due. Immediate payment is required to avoid collection action." (bold) |

Messages are stored in `Report.config.statement.comments` — users can edit
the tone for their business without touching code.

## UI Components

### Collections Queue (Accounting Dashboard)

Four summary cards at top:
- **DSO** — Days Sales Outstanding (the single number that measures collection effectiveness)
- **Cash This Week** — payments received in last 7 days
- **Open Actions** — collection actions in progress (with overdue count)
- **Promises Broken** — collection actions past deadline with no payment

Below: top 10 past-due customers sorted by balance. Each row shows:
- Customer name and account number
- Balance due (red)
- Days late (color-coded badge)
- Open invoice count
- Last payment date and amount

**Interactions:**
- Click → opens customer detail
- Shift-click → creates collection Action assigned to customer

### Customer Health Card (Customer Detail Page)

Compact panel at top of customer detail tab showing:
- **Aging bar** — colored visualization (green/amber/orange/red proportional)
- **Balance Due / Credit Limit / Available** — with over-limit in red
- **Open Invoices** — count and total
- **Avg Days to Pay** — with trend arrow (improving/stable/deteriorating)
- **Last Payment** — date and amount
- **Health Score badge** — Green (Good Standing) / Yellow (Watch) / Red (At Risk)

## Backend Services

### `get_collections_dashboard()`

`POST /wcapi/manage/` with `action: "get_collections_dashboard"`

Returns: `top_past_due`, `dso_current`, `cash_this_week`, `collection_actions`, `promises_broken`

### `get_customer_health(customer_id)`

`POST /wcapi/manage/` with `action: "get_customer_health"`, `params: { customer_id }`

Returns: `aging`, `credit_limit`, `available_credit`, `payment_velocity`,
`velocity_trend`, `last_payment`, `open_invoices`, `health_score`

## Alice's Role

- Flags customers whose payment velocity is deteriorating (paid in 20 days last quarter, now averaging 45)
- Auto-creates collection Actions when invoices cross aging thresholds (30/60/90)
- Tracks promise-to-pay dates and alerts when broken
- Recommends which customers to call first (largest balance x days late x payment history)
- Monitors statement effectiveness — flags customers with no improvement after 3 consecutive statements
- Tracks `dt_last_statement` to prevent over-mailing

## File Locations

| What | Where |
|------|-------|
| Financial structure defaults | `apps/orgs/models/constants.py` → `default_financial()` |
| Collections dashboard service | `apps/accounts/services/collections_dashboard.py` |
| Accounting dashboard service | `apps/accounts/services/accounting_dashboard.py` |
| Financial maintenance | `apps/orgs/services/financial_maintenance.py` |
| Pydantic schemas | `apps/orgs/pydantic_schemas.py` |
| Collections Queue component | `React2025/src/components/collections/CollectionsQueue.tsx` |
| Customer Health Card | `React2025/src/components/collections/CustomerHealthCard.tsx` |
| Statement layout (with dunning) | Report id=409, `config.form` + `config.statement.comments` |
| Manage view action dispatch | `apps/core/views/manage_view.py` → `_ACTION_DISPATCH` |
