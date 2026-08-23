# Transaction Calculations Guide

> **Version**: 1.0  
> **Updated**: 2026-01-14  
> **Scope**: WC3 Backend + R25 Frontend calculation logic  
> **Audience**: Developers working on transaction pricing, totals, and financial logic

---

## Table of Contents

1. [Overview](#overview)
2. [Data Structures](#data-structures)
3. [Line-Level Calculations](#line-level-calculations)
4. [Header-Level Calculations](#header-level-calculations)
5. [Calculation Triggers](#calculation-triggers)
6. [Price Levels & Discounts](#price-levels--discounts)
7. [Tax Calculations](#tax-calculations)
8. [Margin & Cost (Role-Restricted)](#margin--cost-role-restricted)
9. [Payment & Balance Tracking](#payment--balance-tracking)
10. [Transaction Flow (Quote → Order → Invoice)](#transaction-flow-quote--order--invoice)
11. [Frontend vs Backend Responsibility](#frontend-vs-backend-responsibility)
12. [Rounding & Precision Rules](#rounding--precision-rules)
13. [Edge Cases & Validation](#edge-cases--validation)
14. [API Endpoints](#api-endpoints)
15. [Code Examples](#code-examples)

---

## Overview

### Calculation Philosophy

| Principle | Description |
|-----------|-------------|
| **Backend Authoritative** | WC3 is the source of truth for all saved calculations |
| **Frontend Optimistic** | R25 shows real-time estimates; syncs on save |
| **Atomic Updates** | Line changes trigger header recalc in single transaction |
| **Audit Trail** | Original values preserved in `metadata.history` |

### Document Types

| Type | Direction | Has Price | Has Cost | Tracks Fulfillment |
|------|-----------|-----------|----------|-------------------|
| Proposal | Sell | ✅ | ✅ (hidden) | ordered → remaining |
| Sales Order | Sell | ✅ | ✅ (hidden) | staged → invoiced → remaining |
| Invoice | Sell | ✅ | ✅ (hidden) | staged → packed → remaining |
| Purchase Order | Exec | ❌ | ✅ | staged → received → remaining |
| Work Order | Exec | ❌ | ✅ | staged → received → remaining |

---

## Data Structures

### Line Model Fields

```python
# BaseSellLineModel (Proposal, Order, Invoice)
line.quantity = {
    "staged": 10,        # User-entered quantity
    "ordered": 10,       # Original (proposals)
    "invoiced": 0,       # Qty invoiced (orders)
    "packed": 0,         # Qty packed (invoices)
    "remaining": 10,     # staged - fulfilled
    "is_fixed": False,
    "precision": 2,
    "is_blanket": False,
    "increment": 0
}

line.price = {
    "unit": 25.00,           # Sell price per unit
    "unit_base": 30.00,      # List price before discount
    "discount_percent": 10.0,
    "discount_amount": 25.00,
    "extended": 225.00,      # (qty × unit) - discount_amount
    "is_fixed": False,
    "precision": 2
}

line.cost = {
    "unit": 15.00,           # Cost per unit
    "unit_base": 15.00,
    "extended": 150.00,      # qty × unit
    "shipping": 0.00,
    "handling": 0.00,
    "freight": 0.00,
    "commissions": 0.00,
    "tax_rate": 0.0,
    "tax": 0.00,
    "is_fixed": False,
    "precision": 2
}

line.tax = {
    "sales_rate": 8.25,
    "sales": 18.56,          # extended × sales_rate / 100
    "cost_rate": 0.0,
    "cost": 0.0,
    "shipping": 0.0,
    "tax_service_id": 0
}
```

### Header Model Fields

```python
# TransactionBaseModel
transaction.totals = {
    "subtotal": 1000.00,    # Sum of line.price.extended
    "discount": 50.00,      # Header-level discount
    "taxable": 950.00,      # subtotal - discount
    "tax": 78.38,           # taxable × tax_rate / 100
    "shipping": 25.00,      # Shipping charged
    "other": 0.00,          # Misc charges
    "total": 1053.38,       # taxable + tax + shipping + other
    "cost": 600.00,         # Sum of line.cost.extended
    "margin": 453.38,       # total - cost
    "margin_pc": 43.05,     # (margin / total) × 100
    "received": 500.00,     # Payments received (invoices)
    "balance": 553.38       # total - received
}

transaction.finance = {
    "sales_tax_id": 123,
    "sales_tax_name": "CA State + County",
    "sales_tax_rate": 8.25,
    "sales_tax": 78.38,
    "tax_subtotal": 950.00,
    "collection_expense": 0.0,
    "exchange_expense": 0.0
}
```

---

## Line-Level Calculations

### Extended Price Formula

```
extended = (quantity.staged × price.unit) - price.discount_amount
```

**Alternate when discount is percentage:**
```
discount_amount = quantity.staged × price.unit × (price.discount_percent / 100)
extended = (quantity.staged × price.unit) - discount_amount
```

### Extended Cost Formula

```
cost.extended = quantity.staged × cost.unit
```

### Line Tax Formula

```
tax.sales = price.extended × (tax.sales_rate / 100)
tax.cost = cost.extended × (tax.cost_rate / 100)
```

### Line Margin (Internal)

```
line_margin = price.extended - cost.extended
line_margin_pc = (line_margin / price.extended) × 100
```

---

## Header-Level Calculations

### Totals Aggregation

```python
def calculate_header_totals(transaction, lines):
    """Recalculate header totals from lines."""
    
    # Sum line values
    subtotal = sum(line.price.extended for line in lines if not line.item.is_deleted)
    cost_total = sum(line.cost.extended for line in lines if not line.item.is_deleted)
    
    # Apply header discount
    discount = transaction.totals.get('discount', 0) or 0
    taxable = subtotal - discount
    
    # Calculate tax
    tax_rate = transaction.finance.get('sales_tax_rate', 0) or 0
    tax = taxable * (tax_rate / 100)
    
    # Sum other charges
    shipping = transaction.totals.get('shipping', 0) or 0
    other = transaction.totals.get('other', 0) or 0
    
    # Grand total
    total = taxable + tax + shipping + other
    
    # Margin
    margin = total - cost_total
    margin_pc = (margin / total * 100) if total > 0 else 0
    
    # Balance (invoices only)
    received = transaction.totals.get('received', 0) or 0
    balance = total - received
    
    return {
        'subtotal': round(subtotal, 2),
        'discount': round(discount, 2),
        'taxable': round(taxable, 2),
        'tax': round(tax, 2),
        'shipping': round(shipping, 2),
        'other': round(other, 2),
        'total': round(total, 2),
        'cost': round(cost_total, 2),
        'margin': round(margin, 2),
        'margin_pc': round(margin_pc, 2),
        'received': round(received, 2),
        'balance': round(balance, 2),
    }
```

### Calculation Order

```
1. Line extended prices (per line)
2. Line costs (per line)
3. Line taxes (per line, if line-level tax)
4. Header subtotal (sum of lines)
5. Header discount (applied)
6. Taxable amount (subtotal - discount)
7. Header tax (taxable × rate)
8. Header total (taxable + tax + shipping + other)
9. Header margin (total - cost)
10. Header balance (total - received)
```

---

## Calculation Triggers

### When Recalculation Occurs

| Event | Line Recalc | Header Recalc | Backend Required |
|-------|-------------|---------------|------------------|
| Quantity changed | ✅ That line | ✅ | On save |
| Unit price changed | ✅ That line | ✅ | On save |
| Discount % changed | ✅ That line | ✅ | On save |
| Discount $ changed | ✅ That line | ✅ | On save |
| Price level changed | ✅ All lines | ✅ | ✅ Immediate |
| Tax rate changed | ✅ All lines | ✅ | On save |
| Line added | ✅ New line | ✅ | On save |
| Line deleted | ❌ | ✅ | On save |
| Header discount changed | ❌ | ✅ | On save |
| Shipping changed | ❌ | ✅ | On save |
| Payment received | ❌ | ✅ Balance only | ✅ Immediate |

### Frontend Real-Time Updates

```typescript
// R25: useTransactionCalculator hook
const useTransactionCalculator = (transaction: Transaction, lines: TransactionLine[]) => {
  const [totals, setTotals] = useState(transaction.totals);
  
  useEffect(() => {
    // Recalculate on any line change
    const newTotals = calculateHeaderTotals(transaction, lines);
    setTotals(newTotals);
  }, [lines, transaction.finance?.sales_tax_rate, transaction.totals?.discount]);
  
  return totals;
};
```

---

## Price Levels & Discounts

### Price Level Hierarchy

```
1. Contract Price (customer-specific)
2. Quantity Break Price (volume discount)
3. Sale Price (promotional)
4. List Price (default)
```

### Price Level Selection

```python
def get_unit_price(item, customer, quantity, price_level=None):
    """Determine unit price based on hierarchy."""
    
    # 1. Explicit price level override
    if price_level:
        return item.prices.get(price_level, item.price_list)
    
    # 2. Customer contract price
    contract = get_customer_contract(customer, item)
    if contract:
        return contract.price
    
    # 3. Quantity break
    qty_price = get_quantity_break_price(item, quantity)
    if qty_price:
        return qty_price
    
    # 4. Sale price (if active)
    if item.price_sale and item.sale_active:
        return item.price_sale
    
    # 5. List price
    return item.price_list
```

### Discount Types

| Type | Applies To | Formula |
|------|-----------|---------|
| Line % Discount | Single line | `extended = qty × unit × (1 - discount_pc/100)` |
| Line $ Discount | Single line | `extended = (qty × unit) - discount_amt` |
| Header % Discount | All lines | `taxable = subtotal × (1 - discount_pc/100)` |
| Header $ Discount | All lines | `taxable = subtotal - discount_amt` |
| Early Pay Discount | Total | Applied at payment, not in totals |

### Discount Precedence

```
Line discounts applied first → Header discount applied to subtotal
```

---

## Tax Calculations

### Tax Determination Flow

```
1. Check tax_exempt flag on transaction
2. If exempt, tax = 0
3. Get tax jurisdiction from shipping address
4. Look up tax rate from tax service (Avalara, TaxJar, etc.)
5. Apply rate to taxable amount
```

### Tax Exempt Handling

```python
def calculate_tax(transaction, taxable_amount):
    if transaction.tax_exempt:
        return {
            'tax': 0,
            'tax_rate': 0,
            'tax_exempt_id': transaction.tax_exempt_id
        }
    
    # Get rate from tax service or stored rate
    rate = get_tax_rate(transaction)
    tax = taxable_amount * (rate / 100)
    
    return {
        'tax': round(tax, 2),
        'tax_rate': rate,
        'tax_exempt_id': None
    }
```

### Line-Level vs Header-Level Tax

| Scenario | Tax Calculation Level |
|----------|----------------------|
| Single tax jurisdiction | Header (faster) |
| Multi-ship addresses | Line (each line to different address) |
| Mixed taxable/non-taxable items | Line |
| Tax service integration | Usually line |

---

## Margin & Cost (Role-Restricted)

### Role Requirements

| Data | Minimum Role | Notes |
|------|--------------|-------|
| `price.*` | user | Customer-visible pricing |
| `cost.unit` | manager | Unit cost |
| `cost.extended` | manager | Extended cost |
| `totals.cost` | manager | Total cost |
| `totals.margin` | manager | Dollar margin |
| `totals.margin_pc` | manager | Percentage margin |

### Margin Calculation

```python
# Line level
line_margin = line.price.extended - line.cost.extended
line_margin_pc = (line_margin / line.price.extended * 100) if line.price.extended > 0 else 0

# Header level (after all charges)
header_margin = totals.total - totals.cost
header_margin_pc = (header_margin / totals.total * 100) if totals.total > 0 else 0
```

### Minimum Margin Enforcement

```python
def validate_margin(transaction, min_margin_pc=15):
    """Warn if margin below threshold."""
    if transaction.totals.margin_pc < min_margin_pc:
        return {
            'warning': f'Margin {transaction.totals.margin_pc}% below minimum {min_margin_pc}%',
            'requires_approval': True
        }
    return {'warning': None, 'requires_approval': False}
```

---

## Payment & Balance Tracking

### Payment Flow (Invoices Only)

```
Invoice Created → balance = total, received = 0
Payment 1 Applied → received += payment, balance = total - received
Payment 2 Applied → received += payment, balance = total - received
Fully Paid → received = total, balance = 0
```

### Overpayment Handling

```python
def apply_payment(invoice, payment_amount):
    new_received = invoice.totals.received + payment_amount
    new_balance = invoice.totals.total - new_received
    
    if new_balance < 0:
        # Overpayment - create credit memo or refund
        overpayment = abs(new_balance)
        return {
            'applied': payment_amount - overpayment,
            'overpayment': overpayment,
            'balance': 0,
            'action': 'create_credit_memo'
        }
    
    return {
        'applied': payment_amount,
        'overpayment': 0,
        'balance': new_balance,
        'action': None
    }
```

### Status Based on Balance

```python
def get_payment_status(invoice):
    balance = invoice.totals.balance
    total = invoice.totals.total
    received = invoice.totals.received
    
    if received == 0:
        return 'unpaid'
    elif balance == 0:
        return 'paid'
    elif balance > 0 and received > 0:
        return 'partial'
    else:
        return 'overpaid'  # Credit balance
```

---

## Transaction Flow (Quote → Order → Invoice)

### Conversion Flow

```
Proposal → Sales Order → Invoice
   ↓           ↓            ↓
quoted     ordered      invoiced
```

### Quantity Tracking Through Flow

```python
# Proposal
proposal_line.quantity = {
    'staged': 100,
    'ordered': 0,      # How many converted to order
    'remaining': 100   # staged - ordered
}

# After converting 60 to Sales Order
proposal_line.quantity.ordered = 60
proposal_line.quantity.remaining = 40

# Sales Order
order_line.quantity = {
    'staged': 60,
    'invoiced': 0,     # How many invoiced
    'remaining': 60    # staged - invoiced
}

# After invoicing 40
order_line.quantity.invoiced = 40
order_line.quantity.remaining = 20

# Invoice
invoice_line.quantity = {
    'staged': 40,
    'packed': 0,       # How many packed/shipped
    'remaining': 40
}
```

### Price Locking

| Stage | Price Behavior |
|-------|---------------|
| Proposal | Prices can change freely |
| Sales Order | Prices locked from proposal (or re-quoted) |
| Invoice | Prices locked from order |

```python
def convert_to_order(proposal):
    order = Order.create_from(proposal)
    for line in order.lines:
        line.price.is_fixed = True  # Lock prices
    return order
```

---

## Frontend vs Backend Responsibility

### Division of Labor

| Task | Frontend (R25) | Backend (WC3) |
|------|----------------|---------------|
| Real-time line math | ✅ Optimistic | ✅ Authoritative |
| Real-time header totals | ✅ Optimistic | ✅ Authoritative |
| Price level lookup | ❌ | ✅ |
| Tax rate lookup | ❌ | ✅ |
| Margin enforcement | ⚠️ Warning only | ✅ Validation |
| Payment application | ❌ | ✅ |
| Inventory check | ❌ | ✅ |

### Sync Strategy

```typescript
// Frontend optimistic calculation
const optimisticTotals = calculateLocally(lines);
setDisplayTotals(optimisticTotals);

// On save, backend recalculates
const response = await api.save(transaction);
setDisplayTotals(response.totals); // Backend authoritative
```

### Conflict Resolution

```
Frontend value !== Backend value?
→ Backend wins
→ Show toast: "Totals updated by server"
```

---

## Rounding & Precision Rules

### Default Precision

| Field | Precision | Rounding |
|-------|-----------|----------|
| Unit price | 2-4 dp | HALF_UP |
| Extended price | 2 dp | HALF_UP |
| Quantity | 0-4 dp | (configurable) |
| Tax rate | 2-4 dp | HALF_UP |
| Tax amount | 2 dp | HALF_UP |
| Percentages | 2 dp | HALF_UP |

### Rounding Implementation

```python
from decimal import Decimal, ROUND_HALF_UP

def round_money(value, places=2):
    """Round monetary value to specified decimal places."""
    d = Decimal(str(value))
    return float(d.quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP))
```

### Penny Rounding Issue

```
10 lines × $33.333... = $333.33 (rounded per line)
vs
Sum first, round once = $333.33

Solution: Round at line level, accept small variance
```

---

## Edge Cases & Validation

### Item ID Immutability

**Critical Security Rule**: Once a line is saved with an `item_id`, that value **cannot be changed** on subsequent updates.

```python
# BaseLineSerializer.validate() enforces this rule:

def validate(self, attrs):
    # ... role-based validation ...
    
    # Prevent item_id changes on existing lines (security backstop)
    # R25 UI is primary defense; this catches malicious API calls
    if self.instance is not None:  # This is an UPDATE
        current_item = getattr(self.instance, 'item', {}) or {}
        current_item_id = current_item.get('item_id')
        
        new_item = attrs.get('item', {}) or {}
        new_item_id = new_item.get('item_id')
        
        # Only reject if new_item_id is provided AND differs from current
        if new_item_id is not None and current_item_id is not None:
            if new_item_id != current_item_id:
                raise serializers.ValidationError({
                    'item': 'Item_id cannot be changed for any line. To change the item, please delete this line and add a new line with the correct item.'
                })
    
    return attrs
```

| Defense Layer | Responsibility | Implementation |
|---------------|----------------|----------------|
| **R25 Frontend** | Primary defense | Make item fields read-only on saved lines, hide item picker |
| **WC3 Backend** | Security backstop | `BaseLineSerializer.validate()` rejects item_id changes |

**Why This Matters**:
- Changing `item_id` breaks audit trails and linked data (inventory, accounting)
- Particularly critical for POs where item changes affect vendor negotiations
- Frontend can be bypassed; backend must enforce

### Zero/Null Handling

```python
def safe_divide(numerator, denominator, default=0):
    """Safe division avoiding ZeroDivisionError."""
    if not denominator or denominator == 0:
        return default
    return numerator / denominator

# Margin % with zero total
margin_pc = safe_divide(margin, total, default=0) * 100
```

### Negative Value Rules

| Field | Allow Negative? | Use Case |
|-------|-----------------|----------|
| Quantity | ❌ No | - |
| Unit price | ⚠️ Credit memo only | Returns |
| Extended | ⚠️ Credit memo only | Returns |
| Discount | ✅ Yes | Surcharge (negative discount) |
| Balance | ✅ Yes | Overpayment credit |

### Validation Rules

```python
VALIDATION_RULES = {
    'quantity.staged': {'min': 0, 'required': True},
    'price.unit': {'min': 0},
    'price.discount_percent': {'min': 0, 'max': 100},
    'totals.total': {'min': 0},
}

def validate_line(line):
    errors = []
    if line.quantity.staged < 0:
        errors.append('Quantity cannot be negative')
    if line.price.discount_percent > 100:
        errors.append('Discount cannot exceed 100%')
    return errors
```

---

## API Endpoints

### Calculation-Related Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/wcapi/save/` | POST | Save & recalculate |
| `/wcapi/transaction/save/` | POST | Save with dirty tracking & calculation verification |
| `/wcapi/calculate/` | POST | Preview calculation without save |
| `/wcapi/price-lookup/` | POST | Get price for item/customer/qty |
| `/wcapi/tax-lookup/` | POST | Get tax rate for address |
| `/wcapi/apply-payment/` | POST | Apply payment to invoice |

### Transaction Save Endpoint (with Verification)

> **Endpoint**: `POST /wcapi/transaction/save/`  
> **Implementation**: `apps/transactions/services/transaction_save.py` + `WCAPITransactionSaveView`

This endpoint provides:
1. **Dirty line tracking** - Skip unchanged lines (`_dirty: false`)
2. **Calculation verification** - Compare R25's values to WC3's authoritative math
3. **Recalculated totals** - Return WC3's authoritative totals for R25 to sync

#### Request Payload

```json
{
  "model_name": "invoice",
  "record": {
    "id": 123,
    "totals": {
      "subtotal": 1000.00,
      "tax": 80.00,
      "total": 1080.00
    },
    "finance": {
      "margin": 250.00,
      "margin_pct": 25.0
    },
    "lines": [
      {
        "id": 1,
        "_dirty": false,
        "quantity": { "qty": 5 },
        "price": { "unit": 100.00, "extended": 500.00 },
        "discount": { "pct": 10, "amt": 50.00 }
      },
      {
        "id": 2,
        "_dirty": true,
        "quantity": { "qty": 10 },
        "price": { "unit": 50.00, "extended": 450.00 },
        "discount": { "pct": 10, "amt": 50.00 }
      }
    ]
  },
  "options": {
    "verify_calculations": true,
    "save_only_dirty": true
  }
}
```

> **Note**: Lines are provided inside `record.lines` (consistent with existing `/wcapi/save/` pattern).
> WC3 loops through this array and processes each line based on its `_dirty` flag.

#### Response (Success)

```json
{
  "header": { "id": 123 },
  "lines": [
    { "id": 1, "action": "skipped", "reason": "not_dirty" },
    { "id": 2, "action": "updated" }
  ],
  "lines_saved": 1,
  "lines_skipped": 1,
  "action": "updated",
  "recalculated_totals": {
    "subtotal": 1000.00,
    "tax": 80.00,
    "total": 1080.00,
    "margin": 250.00,
    "margin_pct": 25.0
  }
}
```

#### Response (Calculation Mismatch)

```json
{
  "detail": "Calculation mismatch",
  "error": "Line 2: 'extended' mismatch - R25: 500.00 vs WC3: 450.00",
  "field": "extended",
  "r25_value": 500.00,
  "wc3_value": 450.00,
  "line_id": 2
}
```

#### Calculation Tolerance

```python
CALC_TOLERANCE = Decimal("0.01")  # $0.01 tolerance
```

This handles rounding differences between JavaScript and Python decimal math.

#### Verified Calculations

| Field | Formula |
|-------|---------|
| `price.extended` | `qty × unit` |
| `discount.amt` | `extended × (pct / 100)` |
| `cost.extended` | `qty × unit` |
| `cost.grossCost` | `cost.extended` |
| `cost.discountCost` | `cost.extended - discount.amt` |
| `totals.subtotal` | `Σ(line.price.extended - line.discount.amt)` |
| `totals.tax` | `subtotal × tax_rate` |
| `totals.total` | `subtotal + tax` |
| `finance.margin` | `subtotal - Σ(line.cost.extended)` |
| `finance.margin_pct` | `(margin / subtotal) × 100` |

### Calculate Preview Endpoint

```python
# POST /wcapi/calculate/
# Request
{
    "model_name": "invoice",
    "record": {
        "id": 123,
        "totals": {"discount": 50},
        "finance": {"sales_tax_rate": 8.25}
    },
    "lines": [
        {"id": 1, "quantity": {"staged": 10}, "price": {"unit": 25}},
        {"id": 2, "quantity": {"staged": 5}, "price": {"unit": 50}}
    ]
}

# Response
{
    "totals": {
        "subtotal": 500.00,
        "discount": 50.00,
        "taxable": 450.00,
        "tax": 37.13,
        "total": 487.13,
        ...
    },
    "lines": [
        {"id": 1, "price": {"extended": 250.00}, ...},
        {"id": 2, "price": {"extended": 250.00}, ...}
    ]
}
```

---

## Code Examples

### R25 Frontend: Line Calculator

```typescript
// src/apps/transactions/utils/lineCalculator.ts

export interface LineCalcResult {
  extended: number;
  discountAmount: number;
  tax: number;
}

export function calculateLine(
  quantity: number,
  unitPrice: number,
  discountPercent: number = 0,
  taxRate: number = 0
): LineCalcResult {
  const gross = quantity * unitPrice;
  const discountAmount = gross * (discountPercent / 100);
  const extended = gross - discountAmount;
  const tax = extended * (taxRate / 100);
  
  return {
    extended: Math.round(extended * 100) / 100,
    discountAmount: Math.round(discountAmount * 100) / 100,
    tax: Math.round(tax * 100) / 100,
  };
}
```

### R25 Frontend: Header Calculator

```typescript
// src/apps/transactions/utils/headerCalculator.ts

export function calculateHeaderTotals(
  lines: TransactionLine[],
  headerDiscount: number = 0,
  taxRate: number = 0,
  shipping: number = 0
): TransactionTotals {
  const activeLines = lines.filter(l => !l.item?.is_deleted);
  
  const subtotal = activeLines.reduce(
    (sum, line) => sum + (line.price?.extended ?? 0), 
    0
  );
  
  const costTotal = activeLines.reduce(
    (sum, line) => sum + (line.cost?.extended ?? 0),
    0
  );
  
  const taxable = subtotal - headerDiscount;
  const tax = taxable * (taxRate / 100);
  const total = taxable + tax + shipping;
  const margin = total - costTotal;
  const marginPc = total > 0 ? (margin / total) * 100 : 0;
  
  return {
    subtotal: round(subtotal),
    discount: round(headerDiscount),
    taxable: round(taxable),
    tax: round(tax),
    shipping: round(shipping),
    total: round(total),
    cost: round(costTotal),
    margin: round(margin),
    margin_pc: round(marginPc),
  };
}

function round(value: number, decimals: number = 2): number {
  return Math.round(value * 10 ** decimals) / 10 ** decimals;
}
```

### WC3 Backend: Recalculate Service

```python
# apps/transactions/services/calculation_service.py

from decimal import Decimal, ROUND_HALF_UP

class TransactionCalculationService:
    """Authoritative calculation service for transactions."""
    
    def recalculate(self, transaction, lines):
        """Full recalculation of transaction and lines."""
        
        # 1. Calculate each line
        for line in lines:
            self._calculate_line(line)
        
        # 2. Aggregate to header
        totals = self._calculate_header(transaction, lines)
        
        # 3. Update transaction
        transaction.totals = totals
        transaction.total = Decimal(str(totals['total']))
        transaction.balance = Decimal(str(totals['balance']))
        
        return transaction, lines
    
    def _calculate_line(self, line):
        """Calculate extended price and cost for a line."""
        qty = Decimal(str(line.quantity.get('staged', 0) or 0))
        
        # Price
        unit_price = Decimal(str(line.price.get('unit', 0) or 0))
        discount_pct = Decimal(str(line.price.get('discount_percent', 0) or 0))
        
        gross = qty * unit_price
        discount_amt = gross * (discount_pct / 100)
        extended = gross - discount_amt
        
        line.price['discount_amount'] = float(self._round(discount_amt))
        line.price['extended'] = float(self._round(extended))
        
        # Cost
        unit_cost = Decimal(str(line.cost.get('unit', 0) or 0))
        cost_extended = qty * unit_cost
        line.cost['extended'] = float(self._round(cost_extended))
        
        return line
    
    def _calculate_header(self, transaction, lines):
        """Aggregate line values to header totals."""
        active_lines = [l for l in lines if not l.item.get('is_deleted')]
        
        subtotal = sum(Decimal(str(l.price.get('extended', 0))) for l in active_lines)
        cost_total = sum(Decimal(str(l.cost.get('extended', 0))) for l in active_lines)
        
        discount = Decimal(str(transaction.totals.get('discount', 0) or 0))
        taxable = subtotal - discount
        
        tax_rate = Decimal(str(transaction.finance.get('sales_tax_rate', 0) or 0))
        tax = taxable * (tax_rate / 100)
        
        shipping = Decimal(str(transaction.totals.get('shipping', 0) or 0))
        other = Decimal(str(transaction.totals.get('other', 0) or 0))
        
        total = taxable + tax + shipping + other
        margin = total - cost_total
        margin_pc = (margin / total * 100) if total > 0 else Decimal(0)
        
        received = Decimal(str(transaction.totals.get('received', 0) or 0))
        balance = total - received
        
        return {
            'subtotal': float(self._round(subtotal)),
            'discount': float(self._round(discount)),
            'taxable': float(self._round(taxable)),
            'tax': float(self._round(tax)),
            'shipping': float(self._round(shipping)),
            'other': float(self._round(other)),
            'total': float(self._round(total)),
            'cost': float(self._round(cost_total)),
            'margin': float(self._round(margin)),
            'margin_pc': float(self._round(margin_pc)),
            'received': float(self._round(received)),
            'balance': float(self._round(balance)),
        }
    
    def _round(self, value, places=2):
        """Round to specified decimal places."""
        return value.quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)
```

---

## Multi-Currency Handling

### Currency Fields

```python
# Transaction-level currency settings
transaction.currency = {
    "code": "EUR",              # Transaction currency (display)
    "base_code": "USD",         # Base/home currency (reporting)
    "exchange_rate": 1.0856,    # EUR to USD rate at time of transaction
    "rate_date": "2026-01-14",  # When rate was locked
    "rate_source": "xe.com",    # Rate provider
}
```

### Exchange Rate Model

```python
# apps/accounts/models/exchange_rate.py
class ExchangeRate(BaseModel):
    currency_base = models.CharField(max_length=3)      # USD
    currency_target = models.CharField(max_length=3)    # EUR
    rate = models.DecimalField(max_digits=18, decimal_places=6)
    effective_date = models.DateField()
    source = models.CharField(max_length=50)
```

### Conversion Formulas

```python
def convert_to_base(amount, exchange_rate):
    """Convert transaction currency to base currency."""
    return amount * exchange_rate

def convert_from_base(amount, exchange_rate):
    """Convert base currency to transaction currency."""
    return amount / exchange_rate

# Example: €100 at rate 1.0856
base_amount = convert_to_base(100, 1.0856)  # $108.56 USD
```

### When Rates Are Locked

| Event | Rate Behavior |
|-------|--------------|
| Proposal created | Current rate, can update |
| Order confirmed | Rate locked |
| Invoice generated | Inherits order rate |
| Payment received | New rate for payment (creates exchange gain/loss) |

### Exchange Gain/Loss

```python
def calculate_exchange_variance(invoice, payment):
    """Calculate gain/loss from rate difference."""
    # Invoice amount in base at invoice rate
    invoice_base = invoice.total * invoice.currency.exchange_rate
    
    # Payment amount in base at payment rate
    payment_base = payment.amount * payment.currency.exchange_rate
    
    # Variance
    variance = payment_base - invoice_base
    return {
        'amount': variance,
        'type': 'gain' if variance > 0 else 'loss'
    }
```

---

## Blanket Orders & Releases

### Blanket Order Structure

```python
# Blanket order = master agreement with total quantity/value
blanket_order = {
    "is_blanket": True,
    "blanket_total_qty": 1000,
    "blanket_total_value": 25000.00,
    "blanket_released_qty": 350,
    "blanket_released_value": 8750.00,
    "blanket_remaining_qty": 650,
    "blanket_remaining_value": 16250.00,
    "expiration_date": "2026-12-31",
}

# Line-level blanket tracking
blanket_line.quantity = {
    "blanket_qty": 500,         # Total committed
    "released_qty": 150,        # Released to orders
    "remaining_qty": 350,       # Available to release
    "is_blanket": True,
}
```

### Release Process

```python
def create_release(blanket_order, release_lines):
    """Create a release order from blanket."""
    release = Order.objects.create(
        parent_id=blanket_order.id,
        parent_type='blanket',
        is_release=True,
    )
    
    for line_spec in release_lines:
        blanket_line = blanket_order.lines.get(id=line_spec['blanket_line_id'])
        release_qty = line_spec['quantity']
        
        # Validate availability
        if release_qty > blanket_line.quantity['remaining_qty']:
            raise ValidationError('Release qty exceeds blanket remaining')
        
        # Create release line
        ReleaseLine.objects.create(
            parent=release,
            blanket_line_id=blanket_line.id,
            quantity={'staged': release_qty},
            price=blanket_line.price,  # Inherit blanket price
        )
        
        # Update blanket line
        blanket_line.quantity['released_qty'] += release_qty
        blanket_line.quantity['remaining_qty'] -= release_qty
        blanket_line.save()
    
    return release
```

### Release Schedule

```python
# Planned release schedule
blanket_order.release_schedule = [
    {"date": "2026-02-01", "qty": 100, "status": "scheduled"},
    {"date": "2026-03-01", "qty": 100, "status": "scheduled"},
    {"date": "2026-04-01", "qty": 100, "status": "scheduled"},
]
```

---

## Bundle & Kit Pricing

### Bundle Types

| Type | Description | Pricing |
|------|-------------|---------|
| **Fixed Bundle** | Components fixed, single price | Bundle price only |
| **Configurable Kit** | Components selectable | Sum of components ± adjustment |
| **Assembly** | Components consumed, new item created | Assembly price |

### Bundle Structure

```python
bundle_line = {
    "item": {
        "item_id": 1001,
        "ida_item": "BUNDLE-STARTER-KIT",
        "is_bundle": True,
        "bundle_type": "fixed",  # fixed, configurable, assembly
    },
    "components": [
        {
            "item_id": 101,
            "ida_item": "WIDGET-A",
            "quantity": 2,
            "unit_price": 25.00,
            "extended": 50.00,
            "included": True,  # Included in bundle price
        },
        {
            "item_id": 102,
            "ida_item": "WIDGET-B",
            "quantity": 1,
            "unit_price": 75.00,
            "extended": 75.00,
            "included": True,
        },
    ],
    "price": {
        "component_total": 125.00,  # Sum of components
        "bundle_price": 99.00,      # Actual charge
        "bundle_discount": 26.00,   # Savings
        "extended": 99.00,
    },
}
```

### Kit Pricing Calculation

```python
def calculate_kit_price(kit_line):
    """Calculate kit price from components."""
    component_total = sum(
        c['quantity'] * c['unit_price'] 
        for c in kit_line['components']
        if c['included']
    )
    
    # Apply kit pricing rule
    if kit_line['item']['bundle_type'] == 'fixed':
        # Fixed bundle price
        return kit_line['price']['bundle_price']
    
    elif kit_line['item']['bundle_type'] == 'configurable':
        # Component sum with optional adjustment
        adjustment = kit_line['price'].get('adjustment', 0)
        return component_total + adjustment
    
    else:
        return component_total
```

---

## Tiered & Matrix Pricing

### Quantity Break Structure

```python
# Item-level quantity breaks
item.pricing_tiers = [
    {"min_qty": 1,    "max_qty": 9,    "price": 100.00},
    {"min_qty": 10,   "max_qty": 49,   "price": 95.00},
    {"min_qty": 50,   "max_qty": 99,   "price": 90.00},
    {"min_qty": 100,  "max_qty": None, "price": 85.00},
]
```

### Price Matrix (Customer × Quantity)

```python
# Multi-dimensional price matrix
price_matrix = {
    "item_id": 101,
    "dimensions": ["customer_tier", "quantity"],
    "tiers": {
        "retail": {
            "1-9": 100.00,
            "10-49": 95.00,
            "50+": 90.00,
        },
        "wholesale": {
            "1-9": 85.00,
            "10-49": 80.00,
            "50+": 75.00,
        },
        "distributor": {
            "1-9": 70.00,
            "10-49": 65.00,
            "50+": 60.00,
        },
    }
}
```

### Tier Lookup Function

```python
def get_tiered_price(item, quantity, customer_tier='retail'):
    """Look up price from tier matrix."""
    matrix = get_price_matrix(item.id)
    
    if not matrix:
        return item.price_list
    
    tier_prices = matrix['tiers'].get(customer_tier, matrix['tiers']['retail'])
    
    for qty_range, price in tier_prices.items():
        min_q, max_q = parse_qty_range(qty_range)
        if min_q <= quantity <= (max_q or float('inf')):
            return price
    
    return item.price_list

def parse_qty_range(range_str):
    """Parse '10-49' or '50+' into (min, max)."""
    if '+' in range_str:
        return int(range_str.replace('+', '')), None
    parts = range_str.split('-')
    return int(parts[0]), int(parts[1])
```

---

## Promotional Codes & Coupons

### Promo Code Structure

```python
class PromoCode(BaseModel):
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    discount_type = models.CharField(choices=[
        ('percent', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('bogo', 'Buy One Get One'),
        ('shipping', 'Free Shipping'),
    ])
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Validity
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Limits
    max_uses = models.IntegerField(null=True)  # Total uses allowed
    max_uses_per_customer = models.IntegerField(default=1)
    current_uses = models.IntegerField(default=0)
    
    # Conditions
    min_order_amount = models.DecimalField(null=True)
    min_quantity = models.IntegerField(null=True)
    applicable_items = models.JSONField(default=list)  # Item IDs or categories
    excluded_items = models.JSONField(default=list)
    customer_groups = models.JSONField(default=list)  # Eligible customer groups
```

### Promo Validation

```python
def validate_promo_code(code, transaction, customer):
    """Validate promo code applicability."""
    try:
        promo = PromoCode.objects.get(code=code.upper())
    except PromoCode.DoesNotExist:
        return {'valid': False, 'error': 'Invalid promo code'}
    
    now = timezone.now()
    
    # Date validity
    if now < promo.start_date or now > promo.end_date:
        return {'valid': False, 'error': 'Promo code expired or not yet active'}
    
    # Usage limits
    if promo.max_uses and promo.current_uses >= promo.max_uses:
        return {'valid': False, 'error': 'Promo code usage limit reached'}
    
    # Customer usage
    customer_uses = PromoUsage.objects.filter(
        promo=promo, customer=customer
    ).count()
    if customer_uses >= promo.max_uses_per_customer:
        return {'valid': False, 'error': 'You have already used this promo code'}
    
    # Minimum order
    if promo.min_order_amount and transaction.totals['subtotal'] < promo.min_order_amount:
        return {
            'valid': False, 
            'error': f'Minimum order ${promo.min_order_amount} required'
        }
    
    # Customer group
    if promo.customer_groups and customer.group not in promo.customer_groups:
        return {'valid': False, 'error': 'Promo code not valid for your account'}
    
    return {'valid': True, 'promo': promo}
```

### Promo Stacking Rules

```python
STACKING_RULES = {
    'percent': {'stackable_with': ['shipping']},
    'fixed': {'stackable_with': ['shipping']},
    'bogo': {'stackable_with': []},  # BOGO doesn't stack
    'shipping': {'stackable_with': ['percent', 'fixed']},
}

def can_stack_promos(promo1, promo2):
    """Check if two promos can be combined."""
    rules = STACKING_RULES.get(promo1.discount_type, {})
    return promo2.discount_type in rules.get('stackable_with', [])
```

---

## Commission Calculations

### Commission Structure

```python
class CommissionPlan(BaseModel):
    name = models.CharField(max_length=100)
    calculation_type = models.CharField(choices=[
        ('percent_revenue', 'Percentage of Revenue'),
        ('percent_margin', 'Percentage of Margin'),
        ('flat_per_unit', 'Flat Amount per Unit'),
        ('tiered', 'Tiered by Volume'),
    ])
    rate = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Conditions
    min_margin_pc = models.DecimalField(null=True)  # Min margin to earn commission
    product_categories = models.JSONField(default=list)  # Eligible categories
```

### Commission Calculation

```python
def calculate_commission(transaction, sales_rep):
    """Calculate commission for a transaction."""
    plan = sales_rep.commission_plan
    
    if not plan:
        return {'commission': 0, 'details': []}
    
    commission_lines = []
    total_commission = 0
    
    for line in transaction.lines.filter(item__is_deleted=False):
        # Check product eligibility
        if plan.product_categories:
            if line.item.get('category') not in plan.product_categories:
                continue
        
        # Check margin threshold
        line_margin_pc = calculate_line_margin_pc(line)
        if plan.min_margin_pc and line_margin_pc < plan.min_margin_pc:
            continue
        
        # Calculate commission
        if plan.calculation_type == 'percent_revenue':
            commission = line.price['extended'] * (plan.rate / 100)
        
        elif plan.calculation_type == 'percent_margin':
            margin = line.price['extended'] - line.cost['extended']
            commission = margin * (plan.rate / 100)
        
        elif plan.calculation_type == 'flat_per_unit':
            commission = line.quantity['staged'] * plan.rate
        
        else:
            commission = 0
        
        commission_lines.append({
            'line_id': line.id,
            'commission': round(commission, 2),
            'basis': plan.calculation_type,
        })
        total_commission += commission
    
    return {
        'commission': round(total_commission, 2),
        'details': commission_lines,
        'plan': plan.name,
    }
```

### Split Commissions

```python
# Multiple reps on a deal
transaction.commission_splits = [
    {"rep_id": 101, "rep_name": "Alice", "split_pc": 60},
    {"rep_id": 102, "rep_name": "Bob", "split_pc": 40},
]

def calculate_split_commissions(transaction):
    """Calculate commissions split among multiple reps."""
    base_commission = calculate_base_commission(transaction)
    
    splits = []
    for split in transaction.commission_splits:
        rep = SalesRep.objects.get(id=split['rep_id'])
        amount = base_commission * (split['split_pc'] / 100)
        splits.append({
            'rep_id': split['rep_id'],
            'rep_name': split['rep_name'],
            'split_pc': split['split_pc'],
            'commission': round(amount, 2),
        })
    
    return splits
```

---

## Credit Limit Enforcement

### Customer Credit Settings

```python
class CustomerCredit(BaseModel):
    customer = models.OneToOneField('orgs.Org', on_delete=models.CASCADE)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    available_credit = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Settings
    credit_hold = models.BooleanField(default=False)
    require_prepayment = models.BooleanField(default=False)
    payment_terms_id = models.IntegerField(null=True)
    
    # Auto-calculated
    open_orders_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    open_invoices_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
```

### Credit Check on Order

```python
def check_credit(customer, order_total):
    """Check if order would exceed credit limit."""
    credit = customer.credit
    
    if credit.credit_hold:
        return {
            'approved': False,
            'reason': 'Account on credit hold',
            'action': 'contact_credit_dept',
        }
    
    # Calculate exposure
    current_exposure = credit.open_orders_total + credit.open_invoices_total
    new_exposure = current_exposure + order_total
    
    if new_exposure > credit.credit_limit:
        over_limit = new_exposure - credit.credit_limit
        return {
            'approved': False,
            'reason': f'Order exceeds credit limit by ${over_limit:.2f}',
            'credit_limit': float(credit.credit_limit),
            'current_exposure': float(current_exposure),
            'order_total': float(order_total),
            'over_limit': float(over_limit),
            'action': 'require_approval',
        }
    
    return {
        'approved': True,
        'available_after': float(credit.credit_limit - new_exposure),
    }
```

### Real-Time Credit Display

```python
def get_credit_summary(customer):
    """Get customer credit summary for UI display."""
    credit = customer.credit
    
    return {
        'credit_limit': float(credit.credit_limit),
        'open_invoices': float(credit.open_invoices_total),
        'open_orders': float(credit.open_orders_total),
        'current_balance': float(credit.current_balance),
        'available_credit': float(credit.available_credit),
        'credit_hold': credit.credit_hold,
        'utilization_pc': round(
            (credit.current_balance / credit.credit_limit) * 100, 1
        ) if credit.credit_limit > 0 else 0,
    }
```

---

## Landed Cost Allocation

### Landed Cost Components

```python
# Header-level landed costs
transaction.landed_cost = {
    "freight": 500.00,
    "duty": 250.00,
    "customs_fees": 75.00,
    "insurance": 50.00,
    "handling": 100.00,
    "total": 975.00,
    "allocation_method": "value",  # value, weight, quantity, manual
}
```

### Allocation Methods

```python
def allocate_landed_cost(transaction, lines, landed_costs):
    """Allocate landed costs to lines."""
    method = landed_costs.get('allocation_method', 'value')
    total_landed = landed_costs['total']
    
    if method == 'value':
        # Allocate by line value proportion
        total_value = sum(l.cost['extended'] for l in lines)
        for line in lines:
            proportion = line.cost['extended'] / total_value if total_value else 0
            line.cost['landed'] = round(total_landed * proportion, 2)
            line.cost['unit_landed'] = round(
                line.cost['landed'] / line.quantity['staged'], 4
            ) if line.quantity['staged'] else 0
    
    elif method == 'weight':
        # Allocate by weight proportion
        total_weight = sum(
            l.physical.get('weight', {}).get('value', 0) * l.quantity['staged']
            for l in lines
        )
        for line in lines:
            line_weight = line.physical.get('weight', {}).get('value', 0) * line.quantity['staged']
            proportion = line_weight / total_weight if total_weight else 0
            line.cost['landed'] = round(total_landed * proportion, 2)
    
    elif method == 'quantity':
        # Equal allocation per unit
        total_qty = sum(l.quantity['staged'] for l in lines)
        per_unit = total_landed / total_qty if total_qty else 0
        for line in lines:
            line.cost['landed'] = round(per_unit * line.quantity['staged'], 2)
    
    elif method == 'manual':
        # Use manually specified allocations
        pass
    
    return lines
```

### Landed Cost in Line

```python
# After allocation
line.cost = {
    "unit": 15.00,              # Base unit cost
    "extended": 150.00,         # qty × unit
    "landed": 14.63,            # Allocated landed cost
    "unit_landed": 1.463,       # Per-unit landed
    "total": 164.63,            # extended + landed
    "unit_total": 16.463,       # Fully loaded unit cost
}
```

---

## Approval Workflows

### Approval Triggers

```python
APPROVAL_TRIGGERS = {
    'low_margin': {
        'condition': lambda t: t.totals['margin_pc'] < 15,
        'approvers': ['sales_manager'],
        'message': 'Margin below 15% threshold',
    },
    'over_credit': {
        'condition': lambda t: not check_credit(t.customer, t.totals['total'])['approved'],
        'approvers': ['credit_manager'],
        'message': 'Order exceeds credit limit',
    },
    'large_order': {
        'condition': lambda t: t.totals['total'] > 50000,
        'approvers': ['sales_manager', 'finance'],
        'message': 'Order over $50,000 requires approval',
    },
    'large_discount': {
        'condition': lambda t: (t.totals['discount'] / t.totals['subtotal'] * 100) > 20 if t.totals['subtotal'] else False,
        'approvers': ['sales_manager'],
        'message': 'Discount exceeds 20%',
    },
    'special_pricing': {
        'condition': lambda t: any(l.price.get('is_manual') for l in t.lines.all()),
        'approvers': ['pricing_admin'],
        'message': 'Contains manually overridden prices',
    },
}
```

### Approval Request Model

```python
class ApprovalRequest(BaseModel):
    transaction_type = models.CharField(max_length=50)
    transaction_id = models.BigIntegerField()
    trigger = models.CharField(max_length=50)
    message = models.TextField()
    status = models.CharField(choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ], default='pending')
    
    requested_by = models.ForeignKey('core.Contact', related_name='approval_requests')
    requested_at = models.DateTimeField(auto_now_add=True)
    
    decided_by = models.ForeignKey('core.Contact', null=True, related_name='approval_decisions')
    decided_at = models.DateTimeField(null=True)
    decision_notes = models.TextField(blank=True)
```

### Workflow Integration

```python
def submit_for_approval(transaction):
    """Check triggers and create approval requests."""
    pending_approvals = []
    
    for trigger_name, trigger_config in APPROVAL_TRIGGERS.items():
        if trigger_config['condition'](transaction):
            approval = ApprovalRequest.objects.create(
                transaction_type=transaction._meta.model_name,
                transaction_id=transaction.id,
                trigger=trigger_name,
                message=trigger_config['message'],
                requested_by=get_current_user(),
            )
            pending_approvals.append({
                'id': approval.id,
                'trigger': trigger_name,
                'message': trigger_config['message'],
                'approvers': trigger_config['approvers'],
            })
    
    if pending_approvals:
        transaction.status = 'pending_approval'
        transaction.save()
    
    return pending_approvals
```

---

## Audit Logging

### Price Change Audit

```python
class PriceAuditLog(BaseModel):
    """Track all pricing changes for compliance."""
    transaction_type = models.CharField(max_length=50)
    transaction_id = models.BigIntegerField()
    line_id = models.BigIntegerField(null=True)
    
    field_changed = models.CharField(max_length=50)  # unit_price, discount, etc.
    old_value = models.DecimalField(max_digits=18, decimal_places=6, null=True)
    new_value = models.DecimalField(max_digits=18, decimal_places=6)
    
    change_reason = models.CharField(max_length=100, blank=True)
    changed_by = models.ForeignKey('core.Contact', on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    
    # Context
    price_level_before = models.CharField(max_length=50, blank=True)
    price_level_after = models.CharField(max_length=50, blank=True)
    approval_id = models.BigIntegerField(null=True)  # If change required approval
```

### Audit Trigger

```python
from django.db.models.signals import pre_save
from django.dispatch import receiver

@receiver(pre_save, sender=InvoiceLine)
def audit_price_changes(sender, instance, **kwargs):
    """Log price changes before save."""
    if not instance.pk:
        return  # New record, skip
    
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    
    # Check for price changes
    fields_to_audit = [
        ('price.unit', 'unit_price'),
        ('price.discount_percent', 'discount_percent'),
        ('price.discount_amount', 'discount_amount'),
    ]
    
    for json_path, field_name in fields_to_audit:
        old_val = get_nested(old.price, json_path.split('.')[1:])
        new_val = get_nested(instance.price, json_path.split('.')[1:])
        
        if old_val != new_val:
            PriceAuditLog.objects.create(
                transaction_type=instance.parent._meta.model_name,
                transaction_id=instance.parent_id,
                line_id=instance.id,
                field_changed=field_name,
                old_value=old_val,
                new_value=new_val,
                changed_by=get_current_user(),
            )
```

---

## Batch Recalculation

### Rate Change Recalculation

```python
from celery import shared_task

@shared_task
def recalculate_after_rate_change(rate_type, old_rate, new_rate, effective_date):
    """Recalculate affected transactions after rate change."""
    
    if rate_type == 'tax':
        # Find open transactions in affected jurisdiction
        affected = Transaction.objects.filter(
            status__in=['draft', 'pending'],
            finance__sales_tax_id=rate_type,
            created_at__gte=effective_date,
        )
    
    elif rate_type == 'exchange':
        affected = Transaction.objects.filter(
            status__in=['draft', 'pending'],
            currency__code=old_rate.currency_target,
        )
    
    results = {'updated': 0, 'errors': []}
    
    for txn in affected:
        try:
            # Update rate
            if rate_type == 'tax':
                txn.finance['sales_tax_rate'] = new_rate
            elif rate_type == 'exchange':
                txn.currency['exchange_rate'] = new_rate
            
            # Recalculate
            recalculate_transaction(txn)
            txn.save()
            results['updated'] += 1
            
        except Exception as e:
            results['errors'].append({
                'transaction_id': txn.id,
                'error': str(e),
            })
    
    return results
```

### Price List Update

```python
@shared_task
def apply_price_list_update(price_list_id, effective_date):
    """Update prices on open quotes/orders from new price list."""
    
    price_list = PriceList.objects.get(id=price_list_id)
    
    # Find affected transactions
    affected_lines = TransactionLine.objects.filter(
        parent__status__in=['draft', 'pending'],
        parent__price_level=price_list.code,
        price__is_fixed=False,  # Don't update locked prices
    )
    
    for line in affected_lines:
        new_price = price_list.get_price(line.item['item_id'])
        if new_price and new_price != line.price['unit']:
            # Log the change
            PriceAuditLog.objects.create(
                line_id=line.id,
                field_changed='unit_price',
                old_value=line.price['unit'],
                new_value=new_price,
                change_reason=f'Price list update: {price_list.code}',
            )
            
            # Update price
            line.price['unit'] = new_price
            line.save()
    
    # Recalculate affected headers
    affected_transactions = Transaction.objects.filter(
        id__in=affected_lines.values_list('parent_id', flat=True).distinct()
    )
    
    for txn in affected_transactions:
        recalculate_transaction(txn)
        txn.save()
```

---

## Partial Payments & Payment Plans

### Payment Allocation

```python
def apply_payment(invoice, payment_amount, payment_method):
    """Apply payment to invoice with partial payment support."""
    
    current_balance = invoice.totals['balance']
    
    if payment_amount >= current_balance:
        # Full payment (possibly overpayment)
        applied = current_balance
        overpayment = payment_amount - current_balance
        new_balance = 0
        status = 'paid'
    else:
        # Partial payment
        applied = payment_amount
        overpayment = 0
        new_balance = current_balance - payment_amount
        status = 'partial'
    
    # Record payment
    payment = Payment.objects.create(
        invoice=invoice,
        amount=payment_amount,
        applied=applied,
        method=payment_method,
        payment_date=timezone.now(),
    )
    
    # Update invoice
    invoice.totals['received'] = (invoice.totals.get('received', 0) or 0) + applied
    invoice.totals['balance'] = new_balance
    invoice.status = status
    invoice.save()
    
    result = {
        'payment_id': payment.id,
        'applied': applied,
        'new_balance': new_balance,
        'status': status,
    }
    
    # Handle overpayment
    if overpayment > 0:
        credit = create_credit_memo(invoice.customer, overpayment, f'Overpayment on INV-{invoice.ida}')
        result['credit_memo_id'] = credit.id
        result['overpayment'] = overpayment
    
    return result
```

### Payment Plan Structure

```python
class PaymentPlan(BaseModel):
    invoice = models.ForeignKey('Invoice', on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    num_installments = models.IntegerField()
    frequency = models.CharField(choices=[
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
    ])
    start_date = models.DateField()
    
    # Calculated
    installment_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    def generate_schedule(self):
        """Generate payment schedule."""
        schedule = []
        remaining = self.total_amount
        
        for i in range(self.num_installments):
            if i == self.num_installments - 1:
                # Last payment gets remainder (handles rounding)
                amount = remaining
            else:
                amount = self.installment_amount
            
            due_date = self.calculate_due_date(i)
            
            schedule.append({
                'installment': i + 1,
                'due_date': due_date,
                'amount': float(amount),
                'status': 'scheduled',
            })
            
            remaining -= amount
        
        return schedule
```

---

## Refunds & Credit Memos

### Credit Memo Creation

```python
def create_credit_memo(customer, amount, reason, source_invoice=None):
    """Create a credit memo for customer."""
    
    credit = CreditMemo.objects.create(
        customer=customer,
        amount=amount,
        reason=reason,
        source_invoice_id=source_invoice.id if source_invoice else None,
        status='open',
    )
    
    # Update customer credit balance
    customer.credit.available_credit += amount
    customer.credit.save()
    
    return credit

def apply_credit_to_invoice(credit_memo, invoice):
    """Apply credit memo to an invoice."""
    
    applicable = min(credit_memo.remaining, invoice.totals['balance'])
    
    # Apply to invoice
    invoice.totals['received'] += applicable
    invoice.totals['balance'] -= applicable
    invoice.save()
    
    # Reduce credit memo
    credit_memo.applied += applicable
    credit_memo.remaining -= applicable
    if credit_memo.remaining == 0:
        credit_memo.status = 'applied'
    credit_memo.save()
    
    # Record application
    CreditApplication.objects.create(
        credit_memo=credit_memo,
        invoice=invoice,
        amount=applicable,
    )
    
    return {
        'applied': applicable,
        'invoice_balance': invoice.totals['balance'],
        'credit_remaining': credit_memo.remaining,
    }
```

### Return/Refund Processing

```python
def process_return(invoice, return_lines):
    """Process a return and create credit memo."""
    
    credit_amount = 0
    
    for return_spec in return_lines:
        line = invoice.lines.get(id=return_spec['line_id'])
        return_qty = return_spec['quantity']
        
        # Calculate credit
        unit_price = line.price['extended'] / line.quantity['staged']
        line_credit = unit_price * return_qty
        credit_amount += line_credit
        
        # Update line quantities (if tracking returns)
        line.quantity['returned'] = line.quantity.get('returned', 0) + return_qty
        line.save()
    
    # Create credit memo
    credit = create_credit_memo(
        customer=invoice.customer,
        amount=credit_amount,
        reason=f'Return on INV-{invoice.ida}',
        source_invoice=invoice,
    )
    
    return {
        'credit_memo_id': credit.id,
        'credit_amount': credit_amount,
    }
```

---

## Performance Optimization

### Debouncing Input Changes

```typescript
// Frontend: Debounce rapid input changes
import { useDebouncedCallback } from 'use-debounce';

const LineEditor: React.FC = () => {
  const [localQty, setLocalQty] = useState(line.quantity?.staged ?? 0);
  
  // Debounce the parent state update
  const debouncedUpdate = useDebouncedCallback(
    (value: number) => {
      onLineChange(line.id, 'quantity.staged', value);
    },
    300 // 300ms debounce
  );
  
  const handleChange = (value: number) => {
    setLocalQty(value);  // Immediate local update
    debouncedUpdate(value);  // Debounced parent update
  };
};
```

### Memoization Strategies

```typescript
// Memoize expensive calculations
const HeaderTotals: React.FC<{ lines: TransactionLine[] }> = ({ lines }) => {
  // Only recalculate when lines actually change
  const totals = useMemo(() => {
    return calculateHeaderTotals(lines);
  }, [lines]);
  
  // Memoize line-level calculations
  const lineCalcs = useMemo(() => {
    return lines.map(line => ({
      id: line.id,
      ...calculateLine(line),
    }));
  }, [lines]);
  
  return <TotalsDisplay totals={totals} />;
};
```

### Batch Updates

```python
# Backend: Batch update multiple lines efficiently
def batch_update_lines(transaction_id, line_updates):
    """Update multiple lines in a single transaction."""
    from django.db import transaction as db_transaction
    
    with db_transaction.atomic():
        txn = Transaction.objects.select_for_update().get(id=transaction_id)
        lines = list(txn.lines.select_for_update().all())
        
        # Apply updates
        for update in line_updates:
            line = next((l for l in lines if l.id == update['line_id']), None)
            if line:
                for field, value in update['changes'].items():
                    set_nested(line, field.split('.'), value)
        
        # Bulk save lines
        Line.objects.bulk_update(lines, ['price', 'quantity', 'cost'])
        
        # Single header recalc
        recalculate_transaction(txn)
        txn.save()
    
    return txn
```

---

## Error Recovery

### Handling Backend Calculation Failures

```typescript
// Frontend: Graceful degradation on calc failure
const useTransactionWithFallback = (transactionId: number) => {
  const [transaction, setTransaction] = useState<Transaction | null>(null);
  const [calcError, setCalcError] = useState<string | null>(null);
  
  const saveWithRetry = async (data: Transaction, lines: TransactionLine[]) => {
    try {
      const result = await wcapi.save({ 
        model_name: 'invoice', 
        record: data, 
        lines 
      });
      setTransaction(result.record);
      setCalcError(null);
      return result;
      
    } catch (error) {
      if (error.code === 'CALCULATION_ERROR') {
        // Backend calc failed - use frontend values
        setCalcError('Server calculation failed. Showing estimated totals.');
        
        // Save without backend recalc
        const fallbackResult = await wcapi.save({
          model_name: 'invoice',
          record: data,
          lines,
          skip_recalc: true,  // Flag to skip backend calc
        });
        
        return fallbackResult;
      }
      throw error;
    }
  };
  
  return { transaction, saveWithRetry, calcError };
};
```

### Calculation Validation

```python
def validate_calculation(transaction, lines):
    """Validate calculated values are consistent."""
    errors = []
    
    # Verify line extended = qty × unit - discount
    for line in lines:
        expected = (
            line.quantity['staged'] * line.price['unit'] 
            - line.price.get('discount_amount', 0)
        )
        if abs(line.price['extended'] - expected) > 0.01:
            errors.append({
                'line_id': line.id,
                'error': f'Extended mismatch: {line.price["extended"]} != {expected}',
            })
    
    # Verify header subtotal = sum of line extended
    line_sum = sum(l.price['extended'] for l in lines if not l.item.get('is_deleted'))
    if abs(transaction.totals['subtotal'] - line_sum) > 0.01:
        errors.append({
            'error': f'Subtotal mismatch: {transaction.totals["subtotal"]} != {line_sum}',
        })
    
    # Verify total = taxable + tax + shipping + other
    expected_total = (
        transaction.totals['taxable'] 
        + transaction.totals['tax']
        + transaction.totals.get('shipping', 0)
        + transaction.totals.get('other', 0)
    )
    if abs(transaction.totals['total'] - expected_total) > 0.01:
        errors.append({
            'error': f'Total mismatch: {transaction.totals["total"]} != {expected_total}',
        })
    
    return {'valid': len(errors) == 0, 'errors': errors}
```

---

## Related Documents

- [03-wcapi-gateway.md](03-wcapi-gateway.md) - API architecture
- [04-wcapi-usage.md](04-wcapi-usage.md) - API usage patterns
- [06-api-conventions.md](06-api-conventions.md) - Request/response formats
- [07-react-integration.md](07-react-integration.md) - Frontend integration

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-14 | 1.0 | Initial document |
| 2026-01-14 | 1.1 | Added multi-currency, blanket orders, bundles, tiered pricing, promos, commissions, credit limits, landed cost, approvals, audit logging, batch recalc, partial payments, refunds, performance, error recovery |
