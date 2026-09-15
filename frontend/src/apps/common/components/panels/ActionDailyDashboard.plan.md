# Action Daily Dashboard — Plan

## What Bill Is Saying

Staff members need a dashboard that answers: **"What did I work on today, and what was it worth?"**

Actions are the work log. Each action has `refs.links` pointing to the transactions it touched — orders, invoices, purchases, payments, customers. The dashboard pulls those links and denormalizes the essential numbers (totals, balances, status) into summary cards. Clicking a card opens that transaction in a new window.

This is the staff member's daily cockpit — not a report, a live view of their work and its dollar value.

## Data Flow

```
User selects: staff member (default: me) + date range (default: today)
    ↓
Fetch: actions where assigned_to = staff AND dt within range
    ↓
For each action: read action.refs.links
    refs.links.order:    [{ id, ida, company, total, status }]
    refs.links.invoice:  [{ id, ida, company, total, balance, status }]
    refs.links.purchase: [{ id, ida, company, total, status }]
    refs.links.payment:  [{ id, ida, amount, status }]
    refs.links.customer: [{ id, ida, company }]
    refs.links.contact:  [{ id, ida, name }]
    ↓
Aggregate by model type into summary cards:
    Orders card:    count, total $, avg $
    Invoices card:  count, total $, open balance $
    Purchases card: count, total $
    Payments card:  count, total $
    Customers card: count (unique)
    ↓
Each card: click → opens list of those transactions in new window
Each row in expanded card: click → opens that specific transaction
```

## UI Layout

```
┌─────────────────────────────────────────────────────────┐
│ Action Dashboard    [Staff ▾]  [Today ▾] [Date Range]   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ ORDERS   │ │ INVOICES │ │PURCHASES │ │ PAYMENTS │   │
│  │    3     │ │    2     │ │    1     │ │    4     │   │
│  │ $2,698   │ │ $1,890   │ │  $563    │ │ $1,200   │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│                                                         │
│  Actions (7)                                            │
│  ┌─────────────────────────────────────────────────────┐│
│  │ Follow up on qq_SO-001     order  $899  open       ││
│  │ Review PO pricing          purch  $563  open       ││
│  │ Call Mike re: delivery     contact      —          ││
│  │ Process payment #4421      payment $300  applied   ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

## Component: ActionDailyDashboard

**File:** `src/apps/common/components/panels/ActionDailyDashboard.tsx`

### Props
```tsx
interface ActionDailyDashboardProps {
  /** Default staff contact id (current user) */
  defaultStaffId?: number;
  /** Restrict to specific date (default: today) */
  defaultDate?: string;
}
```

### Subcomponents

1. **StaffPicker** — dropdown of is_staff contacts. Default: current user.
2. **DateRangePicker** — presets (Today, Yesterday, This Week, This Month) + custom range.
3. **SummaryCards** — row of `DbCard` components, one per model type. Each shows count + dollar total. Click expands to show individual transactions.
4. **ActionList** — `DbColumns` list of actions for the selected staff + date range. Each row shows action name, linked model type, linked value, status.

### DbCard (new micro-component)

```tsx
interface DbCardProps {
  label: string;         // "Orders"
  count: number;         // 3
  value?: number;        // 2698.50
  sublabel?: string;     // "open balance: $808"
  onClick?: () => void;  // expand or open
  children?: ReactNode;  // expanded content (list of transactions)
}
```

Styled with `--db-*` variables. Click toggles expansion showing the individual transaction rows. Each row is a `db-list-row` — click opens transaction in new window via `window.open`.

### Action refs.links Structure

Actions already have a refs JSON field. The links should carry denormalized essentials so the dashboard doesn't need to fetch each transaction:

```json
{
  "refs": {
    "links": {
      "order": [{
        "id": 42,
        "ida": "qq_SO-001",
        "company": "Metro Baseball Academy",
        "total": 899.50,
        "status": "open",
        "model": "order"
      }],
      "purchase": [{
        "id": 15,
        "ida": "qq_PO-001",
        "company": "Diamond Pro Equipment",
        "total": 563.11,
        "status": "open",
        "model": "purchase"
      }]
    }
  }
}
```

**Rule:** The denormalized summary is a cache. The transaction record is truth. The summary is written when the action is created/linked and refreshed when the action is opened. Stale summaries are acceptable — they show what the value was when the staff member touched it.

### API

One call: `wcapi/get/action` with filters:
- `assigned_to` = staff contact id
- `dt_created__gte` / `dt_created__lte` = date range
- Include refs in response (already standard)

No new endpoints needed. The dashboard aggregates client-side from the refs.links arrays.

### Card Click → Transaction Window

```tsx
const openTransaction = (model: string, id: number) => {
  const path = getModelDetailPath(model, id);
  window.open(path, `${model}-${id}`, 'width=900,height=700');
};
```

Uses existing `getModelDetailPath` utility from panels/index.

## What Needs to Exist First

1. **is_staff qq_ contacts** — 4 staff members (not yet created)
2. **Actions with refs.links** — 4 per staff, linked to qq_SO-001, qq_PO-001, and demo contacts
3. **DbCard component** — small, theme-aware card using --db-* variables
4. **ActionDailyDashboard component** — composes StaffPicker + DateRange + SummaryCards + ActionList

## Build Order

1. Seed 4 is_staff qq_ contacts (qq_s1 through qq_s4)
2. Seed 4 actions per staff with refs.links to transactions
3. Build DbCard (tiny — 30 lines)
4. Build ActionDailyDashboard using DbColumns + DbCard
5. Add route / tab for dashboard access

## Naming

- Component: `ActionDailyDashboard`
- File: `ActionDailyDashboard.tsx`
- CSS: uses existing `--db-*` variables + `db-list-row`, `db-section-header` classes
- Route: TBD — could be a tab in DataBrowser or a standalone `/dashboard/actions` page
