# Org Financials - Type-Keyed Financial Structure

## Overview

Organizations in CommerceExpert can have multiple roles: customer, vendor, rep, employee, manufacturer. Each role has distinct financial tracking needs. The `financial` JSON field on `OrgBase` uses a **type-keyed structure** where each org role has its own section with relevant metrics.

## Structure

```python
financial = {
    "common": { ... },        # Shared by all types
    "customer": { ... },      # AR: what they owe us
    "vendor": { ... },        # AP: what we owe them
    "rep": { ... },           # Commission tracking
    "employee": { ... },      # Payroll/expenses
    "manufacturer": { ... },  # Supply chain
    "fx": { ... },            # Currency impact
}
```

### Multi-Type Support

An org can be multiple types simultaneously. For example:
- A manufacturer who is also a vendor
- A customer who is also a rep

Each applicable section gets populated independently.

## Section Details

### `common` - All Org Types

```python
"common": {
    "currency": "USD",
    "account": {
        "dt_opened": None,
        "dt_last_activity": None,
        "hold": False,        # Credit hold
        "cod_only": False,
        "inactive": False,
    },
    "rating": {
        "internal": None,     # A/B/C or 1-10
        "comments": "",
        "credit_score": None,
    },
    "settings": {
        "discount_pct": 0,
        "tax_exempt": False,
        "tax_exempt_id": "",
        "terms_id": None,
        "notes": "",
    },
}
```

### `customer` - Accounts Receivable

Tracks what customers owe us and their buying behavior.

| Category | Fields | Purpose |
|----------|--------|---------|
| **credit** | limit, high, available | Credit management |
| **balances** | due, current, open_orders, total_exposure | AR totals |
| **aging** | future, period_1, period_2, period_3 | Overdue buckets (30/60/90) |
| **payment** | days_avg_paid, days_pay, dt_last_payment | Payment history |
| **sales** | mtd, ytd, lifetime, dt_last_sale | Revenue tracking |
| **margin** | mtd, ytd, pct | Profitability |
| **returns** | mtd, ytd, count | Return tracking |
| **deposits** | unapplied | Prepayments |
| **collection** | cost_mtd, cost_ytd, cost_alltime | Collection costs |
| **stats** | proposals, orders, invoices, payments | Transaction counts/values |
| **complaints** | our_fault, their_fault, unresolved, costs | Issue tracking |
| **small_stings** | received, issued, by_category | Crowdsourced error fines |

### `vendor` - Accounts Payable

Tracks what we owe vendors.

| Category | Fields | Purpose |
|----------|--------|---------|
| **credit** | limit, terms_days | Their credit terms to us |
| **balances** | due, current, open_pos | AP totals |
| **aging** | future, period_1, period_2, period_3 | What we owe by age |
| **purchases** | mtd, ytd, lifetime | Spend tracking |
| **costs** | mtd, ytd | Cost of goods |
| **payments_made** | mtd, ytd, dt_last_payment | Our payment history |
| **stats** | purchases | PO counts/values |
| **complaints** | our_fault, their_fault, unresolved, costs | Issue tracking |
| **small_stings** | received, issued, by_category | Error fines |

### `rep` - Sales Representative

Tracks commissions and sales credited.

| Category | Fields | Purpose |
|----------|--------|---------|
| **commissions** | mtd, ytd, lifetime, pending, paid, rate_pct | Commission tracking |
| **sales_credited** | mtd, ytd, lifetime | Sales attributed to rep |
| **customers_count** | number | Active customer count |
| **stats** | proposals, orders | Activity tracking |

### `employee` - Payroll & Expenses

Tracks employee compensation and expenses.

| Category | Fields | Purpose |
|----------|--------|---------|
| **payroll** | salary, rate_hourly, rate_type | Compensation |
| **expenses** | mtd, ytd, pending | Expense tracking |
| **commissions** | mtd, ytd | If applicable |
| **time** | hours_mtd, hours_ytd | Time tracking |

### `manufacturer` - Supply Chain

Tracks manufacturer relationships.

| Category | Fields | Purpose |
|----------|--------|---------|
| **purchases** | mtd, ytd, lifetime | Buy volume |
| **rebates** | earned_ytd, received_ytd, pending | Rebate tracking |
| **pricing_tier** | string | Pricing level |
| **lead_time_days** | number | Typical lead time |
| **freight_terms** | string | Shipping terms |
| **min_order** | number | Minimum order amount |
| **stats** | purchases | PO tracking |

### `fx` - Currency Impact

Tracks foreign exchange gains/losses for multi-currency orgs.

```python
"fx": {
    "gain_loss_mtd": 0,
    "gain_loss_ytd": 0,
    "gain_loss_alltime": 0,
}
```

## Small Stings Feature

A novel feature for **crowdsourced error tracking with financial consequences**. Partners can "fine" each other for errors, forcing accountability onto the P&L.

```python
"small_stings": {
    "received": {         # Fines we owe (our errors)
        "count": 0,
        "value": 0,
        "paid": 0,
        "pending": 0,
    },
    "issued": {           # Fines they owe (their errors)
        "count": 0,
        "value": 0,
        "collected": 0,
        "pending": 0,
    },
    "by_category": {
        "shipping": {"count": 0, "value": 0},
        "billing": {"count": 0, "value": 0},
        "quality": {"count": 0, "value": 0},
        "service": {"count": 0, "value": 0},
        "other": {"count": 0, "value": 0},
    },
}
```

**ROI Analysis:**
```
Net Customer Value = lifetime.margin 
                   - collection.cost_alltime 
                   - small_stings.received.value
                   + small_stings.issued.collected
```

## Implementation

### Django Backend

**Location:** `apps/orgs/models/constants.py`

```python
def default_financial():
    """Type-keyed financial profile for orgs."""
    return {
        "common": { ... },
        "customer": { ... },
        "vendor": { ... },
        "rep": { ... },
        "employee": { ... },
        "manufacturer": { ... },
        "fx": { ... },
    }
```

### Migration Command

```bash
# Dry run
python manage.py migrate_financial_structure --dry-run

# Apply migration
python manage.py migrate_financial_structure

# Single org
python manage.py migrate_financial_structure --org-id 123
```

**Location:** `apps/orgs/management/commands/migrate_financial_structure.py`

The migration:
1. Detects old flat structure vs new type-keyed structure
2. Maps old fields to appropriate type sections based on `org_type`
3. Deep-merges with defaults to ensure all keys exist

### React Frontend

**Types:** `src/apps/orgs/types/orgTypes.ts`

Comprehensive TypeScript interfaces:
- `OrgFinancialCommon`
- `OrgFinancialCustomer`
- `OrgFinancialVendor`
- `OrgFinancialRep`
- `OrgFinancialEmployee`
- `OrgFinancialManufacturer`
- `OrgFx`
- `OrgFinancial` (union type)

**Component:** `src/apps/orgs/components/OrgFinancialsPanel.tsx`

Tabbed panel that shows relevant tabs based on org type:
- Customer sees: Common, Customer tabs
- Vendor sees: Common, Vendor tabs
- Multi-type org sees: All applicable tabs

## Querying

### PostgreSQL JSON Queries

```sql
-- Customers with high aging
SELECT display_name, financial->'customer'->'aging'->'period_3' as overdue_90
FROM orgs_orgbase
WHERE org_type = 'customer'
  AND (financial->'customer'->'aging'->'period_3')::int > 0;

-- Profitable customers (margin > collection cost)
SELECT display_name,
       (financial->'customer'->'sales'->'lifetime')::numeric as lifetime_sales,
       (financial->'customer'->'collection'->'cost_alltime')::numeric as collection_cost
FROM orgs_orgbase
WHERE org_type = 'customer'
  AND (financial->'customer'->'sales'->'lifetime')::numeric > 
      (financial->'customer'->'collection'->'cost_alltime')::numeric * 10;

-- Reps with high pending commissions
SELECT display_name, financial->'rep'->'commissions'->'pending' as pending
FROM orgs_orgbase
WHERE org_type = 'rep'
  AND (financial->'rep'->'commissions'->'pending')::numeric > 1000;
```

### Django ORM

```python
from django.db.models import F
from django.db.models.functions import Cast
from django.db.models import FloatField

# Customers on credit hold
OrgBase.objects.filter(
    org_type='customer',
    financial__common__account__hold=True
)

# High-value customers
OrgBase.objects.filter(
    org_type='customer',
    financial__customer__sales__lifetime__gt=100000
)
```

## Future Enhancements

1. **Periodic rollup job** - Nightly task to recalculate MTD/YTD from transactions
2. **Aging job** - Daily recalculation of aging buckets
3. **Credit alerts** - Notifications when customers exceed limits
4. **Small stings workflow** - UI for creating/approving error fines
5. **Profitability dashboard** - Visual analysis of customer/vendor ROI
