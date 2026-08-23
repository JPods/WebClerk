# Orgs Financial Object Structure Plan

**Source Reference**: `/00WebClerk19/Project/Sources/TableForms/2/Input/form.4DForm` (Customer table)

## Current State

The `financial` JSON field on `OrgBase` is minimally defined:
```python
def default_financial():
    return {"credit": {}, "balances": {}, "due_buckets": [], "metrics": {}}
```

## Proposed Structure

Based on the legacy 4D Customer form fields, here is the proposed expanded structure:

### 1. Credit & Account Management (`credit`)

| Key | Type | 4D Source | Description |
|-----|------|-----------|-------------|
| `limit` | decimal | creditLimit:37 | Credit limit for the org |
| `used` | decimal | (computed) | Current credit utilized |
| `high` | decimal | highCredit:38 | Historical highest credit reached |
| `approval` | string | creditApproval:39 | Credit approval notes/status |
| `discount_pct` | decimal | discount:36 | Default discount percentage (0-100) |
| `tax_exempt_id` | string | taxExemptid:56 | Tax exemption certificate ID |
| `duns_number` | string | dunsNumber:86 | D&B DUNS number |
| `db_score` | string | dbScore:87 | D&B credit score |

```python
"credit": {
    "limit": 0,
    "used": 0,
    "high": 0,
    "approval": "",
    "discount_pct": 0,
    "tax_exempt_id": "",
    "duns_number": "",
    "db_score": ""
}
```

### 2. Balances / AR (`balances`)

| Key | Type | 4D Source | Description |
|-----|------|-----------|-------------|
| `total_exposure` | decimal | balanceTotalExposure:104 | Total AR + open orders |
| `open_orders` | decimal | balanceOpenOrders:78 | Open orders balance |
| `total_due` | decimal | balanceDue:42 | Total balance due |
| `current` | decimal | balanceCurrent:41 | Current period balance |
| `future_due` | decimal | futureDue:85 | Future dated invoices |

```python
"balances": {
    "total_exposure": 0,
    "open_orders": 0,
    "total_due": 0,
    "current": 0,
    "future_due": 0
}
```

### 3. Aging Buckets (`aging`)

Standard aging buckets from the 4D fields balPastPeriod1/2/3:

| Key | Type | 4D Source | Description |
|-----|------|-----------|-------------|
| `period_1` | decimal | balPastPeriod1:43 | 1-30 days past due |
| `period_2` | decimal | balPastPeriod2:44 | 31-60 days past due |
| `period_3` | decimal | balPastPeriod3:45 | 61-90+ days past due |

```python
"aging": {
    "period_1": 0,  # 1-30 days
    "period_2": 0,  # 31-60 days
    "period_3": 0   # 61-90+ days
}
```

### 4. Payment Activity (`payment`)

| Key | Type | 4D Source | Description |
|-----|------|-----------|-------------|
| `terms` | string | terms:33 | Payment terms code (Net30, etc) |
| `terms_days` | int | daysPay:40 | Payment terms in days |
| `avg_days_paid` | int | daysAvgPaid:55 | Average days to pay invoices |
| `dt_last_payment` | int | lastPayDate:51 | Last payment date (ms epoch) |
| `invoice_count` | int | invoiceCount:20 | Total invoice count |
| `bad_check` | bool | badCheck:34 | Bad check flag |
| `dt_bad_check` | int | badCheckDate:35 | Bad check date (ms epoch) |

```python
"payment": {
    "terms": "",
    "terms_days": 0,
    "avg_days_paid": 0,
    "dt_last_payment": None,
    "invoice_count": 0,
    "bad_check": False,
    "dt_bad_check": None
}
```

### 5. Sales Metrics (`sales`)

| Key | Type | 4D Source | Description |
|-----|------|-----------|-------------|
| `mtd` | decimal | salesMTD:46 | Sales month-to-date |
| `ytd` | decimal | salesYTD:47 | Sales year-to-date |
| `last_year` | decimal | salesLastYr:48 | Sales last year |
| `dt_last_sale` | int | lastSaleDate:49 | Last sale date (ms epoch) |

```python
"sales": {
    "mtd": 0,
    "ytd": 0,
    "last_year": 0,
    "dt_last_sale": None
}
```

### 6. Cost Metrics (`costs`)

| Key | Type | 4D Source | Description |
|-----|------|-----------|-------------|
| `mtd` | decimal | costsMTD:76 | Costs month-to-date |
| `ytd` | decimal | costsYTD:75 | Costs year-to-date |

```python
"costs": {
    "mtd": 0,
    "ytd": 0
}
```

### 7. Settings (`settings`)

| Key | Type | 4D Source | Description |
|-----|------|-----------|-------------|
| `tax_juris` | string | taxJuris:65 | Tax jurisdiction code |
| `currency` | string | currency:89 | Currency code (USD, etc) |
| `division` | int | division:70 | Division code |
| `mfr_location_id` | int | mfrLocationid:67 | Manufacturer location ID |
| `min_opening_order` | decimal | minimumOpening:118 | Minimum opening order value |
| `min_reorder` | decimal | minimumReorder:119 | Minimum reorder value |
| `service_hr_avail` | decimal | serviceHrAvail:82 | Service hours available |

```python
"settings": {
    "tax_juris": "",
    "currency": "USD",
    "division": None,
    "mfr_location_id": None,
    "min_opening_order": 0,
    "min_reorder": 0,
    "service_hr_avail": 0
}
```

---

## Complete Proposed `default_financial()` 

```python
def default_financial():
    """Financial data for organizations.
    
    Structure:
    - credit: Credit limits, approval, discount, tax exempt
    - balances: AR balances and exposure
    - aging: Past due aging buckets
    - payment: Payment terms, history, bad check status
    - sales: MTD/YTD sales metrics
    - costs: MTD/YTD cost metrics  
    - settings: Tax, currency, minimums
    """
    return {
        "credit": {
            "limit": 0,
            "used": 0,
            "high": 0,
            "approval": "",
            "discount_pct": 0,
            "tax_exempt_id": "",
            "duns_number": "",
            "db_score": ""
        },
        "balances": {
            "total_exposure": 0,
            "open_orders": 0,
            "total_due": 0,
            "current": 0,
            "future_due": 0
        },
        "aging": {
            "period_1": 0,
            "period_2": 0,
            "period_3": 0
        },
        "payment": {
            "terms": "",
            "terms_days": 0,
            "avg_days_paid": 0,
            "dt_last_payment": None,
            "invoice_count": 0,
            "bad_check": False,
            "dt_bad_check": None
        },
        "sales": {
            "mtd": 0,
            "ytd": 0,
            "last_year": 0,
            "dt_last_sale": None
        },
        "costs": {
            "mtd": 0,
            "ytd": 0
        },
        "settings": {
            "tax_juris": "",
            "currency": "USD",
            "division": None,
            "mfr_location_id": None,
            "min_opening_order": 0,
            "min_reorder": 0,
            "service_hr_avail": 0
        }
    }
```

---

## Implementation Tasks

1. [ ] Update `default_financial()` in `apps/orgs/models/constants.py`
2. [ ] Create migration to backfill existing orgs with merged financial data
3. [ ] Update Pydantic schema `OrgSnapshot` to validate financial structure
4. [ ] Add helper methods to `OrgBase`:
   - `credit_utilization()` - already exists, update as needed
   - `update_balances()` - recalculate from AR data
   - `update_sales_metrics()` - update MTD/YTD from invoices
5. [ ] Update admin to display key financial fields
6. [ ] Add serializer fields for financial sub-objects

## Migration Strategy

For existing orgs with partial/empty `financial` data:
- Deep merge new defaults into existing data
- Preserve any existing values
- Use management command: `python manage.py fix_org_financial_defaults`
