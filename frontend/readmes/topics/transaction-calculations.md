# Transaction Calculations - Frontend Guide

> **Version**: 1.0  
> **Updated**: 2026-01-14  
> **Scope**: React2025 frontend calculation logic  
> **Related**: [WC3 08-transaction-calculations.md](../../webClerk3/readmes/08-transaction-calculations.md)

---

## Overview

This document covers how R25 handles transaction math in the UI. The backend (WC3) is **authoritative** - frontend calculations are **optimistic** for real-time UX.

### Key Principle

```
User types → Frontend calculates instantly → Display updates
User saves → Backend recalculates → Frontend syncs to backend values
```

---

## Hooks & Utilities

### File Structure

```
src/apps/transactions/
├── hooks/
│   ├── useLineCalculator.ts      # Single line math
│   ├── useHeaderCalculator.ts    # Header totals aggregation
│   └── useTransactionSync.ts     # Backend sync on save
├── utils/
│   ├── lineCalculator.ts         # Pure calculation functions
│   ├── headerCalculator.ts       # Pure aggregation functions
│   └── formatters.ts             # Currency/number formatting
```

---

## Line-Level Calculations

### useLineCalculator Hook

> **Note**: This hook calculates both price and cost fields for flexibility across transaction types:
> - **Sales transactions** (Sales Order, Invoice, Proposal): Use `price` fields as primary values - these are customer-facing documents
> - **Purchase transactions** (Purchase Order, Work Order): Use `cost` fields as primary values - these are internal/vendor-facing documents
>
> For POs and Work Orders, the `grossCost` and `discountCost` calculations enable proper vendor discount tracking and line total displays.

```typescript
// src/apps/transactions/hooks/useLineCalculator.ts

import { useMemo, useCallback } from 'react';
import type { TransactionLine } from '../types/transactionTypes';

interface LineCalculation {
  gross: number;
  discountAmount: number;
  extended: number;
  grossCost: number;
  discountCost: number;
  costExtended: number;
  margin: number;
  marginPc: number;
}

export function useLineCalculator(line: TransactionLine): LineCalculation {
  return useMemo(() => {
    const qty = line.quantity?.staged ?? 0;
    const unitPrice = line.price?.unit ?? 0;
    const discountPc = line.price?.discount_percent ?? 0;
    const unitCost = line.cost?.unit ?? 0;
    const discountCostPc = line.cost?.discount_percent ?? 0;
    
    // Price calculations
    const gross = qty * unitPrice;
    const discountAmount = gross * (discountPc / 100);
    const extended = gross - discountAmount;
    
    // Cost calculations
    const grossCost = qty * unitCost;
    const discountCost = grossCost * (discountCostPc / 100);
    const costExtended = grossCost - discountCost;
    
    // Margin (internal use only)
    const margin = extended - costExtended;
    const marginPc = extended > 0 ? (margin / extended) * 100 : 0;
    
    return {
      gross: round(gross),
      discountAmount: round(discountAmount),
      extended: round(extended),
      grossCost: round(grossCost),
      discountCost: round(discountCost),
      costExtended: round(costExtended),
      margin: round(margin),
      marginPc: round(marginPc),
    };
  }, [
    line.quantity?.staged,
    line.price?.unit,
    line.price?.discount_percent,
    line.cost?.unit,
  ]);
}

function round(value: number, decimals = 2): number {
  return Math.round(value * 10 ** decimals) / 10 ** decimals;
}
```

### Inline Line Editor

```typescript
// Example: Quantity input with real-time extended update

const LineQuantityInput: React.FC<{
  line: TransactionLine;
  onChange: (field: string, value: number) => void;
}> = ({ line, onChange }) => {
  const calc = useLineCalculator(line);
  
  return (
    <div className="flex items-center gap-4">
      <input
        type="number"
        value={line.quantity?.staged ?? 0}
        onChange={(e) => onChange('quantity.staged', parseFloat(e.target.value) || 0)}
        className="w-20 text-right"
      />
      <span className="text-sm text-slate-500">×</span>
      <span className="w-24 text-right">{formatCurrency(line.price?.unit)}</span>
      <span className="text-sm text-slate-500">=</span>
      <span className="w-28 text-right font-medium">{formatCurrency(calc.extended)}</span>
    </div>
  );
};
```

---

## Header-Level Calculations

### useHeaderCalculator Hook

```typescript
// src/apps/transactions/hooks/useHeaderCalculator.ts

import { useMemo } from 'react';
import type { Transaction, TransactionLine, TransactionTotals } from '../types/transactionTypes';

export function useHeaderCalculator(
  transaction: Transaction,
  lines: TransactionLine[]
): TransactionTotals {
  return useMemo(() => {
    // Filter out deleted lines
    const activeLines = lines.filter(l => !l.item?.is_deleted);
    
    // Sum line values
    const subtotal = activeLines.reduce(
      (sum, line) => sum + (line.price?.extended ?? 0),
      0
    );
    
    const costTotal = activeLines.reduce(
      (sum, line) => sum + (line.cost?.extended ?? 0),
      0
    );
    
    // Header adjustments
    const discount = transaction.totals?.discount ?? 0;
    const taxable = subtotal - discount;
    
    // Tax
    const taxRate = transaction.finance?.sales_tax_rate ?? 0;
    const tax = transaction.tax_exempt ? 0 : taxable * (taxRate / 100);
    
    // Other charges
    const shipping = transaction.totals?.shipping ?? 0;
    const other = transaction.totals?.other ?? 0;
    
    // Totals
    const total = taxable + tax + shipping + other;
    const margin = total - costTotal;
    const marginPc = total > 0 ? (margin / total) * 100 : 0;
    
    // Balance (invoices)
    const received = transaction.totals?.received ?? 0;
    const balance = total - received;
    
    return {
      subtotal: round(subtotal),
      discount: round(discount),
      taxable: round(taxable),
      tax: round(tax),
      shipping: round(shipping),
      other: round(other),
      total: round(total),
      cost: round(costTotal),
      margin: round(margin),
      margin_pc: round(marginPc),
      received: round(received),
      balance: round(balance),
    };
  }, [
    lines,
    transaction.totals?.discount,
    transaction.totals?.shipping,
    transaction.totals?.other,
    transaction.totals?.received,
    transaction.finance?.sales_tax_rate,
    transaction.tax_exempt,
  ]);
}

function round(value: number, decimals = 2): number {
  return Math.round(value * 10 ** decimals) / 10 ** decimals;
}
```

### Totals Display Component

```typescript
// src/apps/transactions/components/TotalsCard.tsx

import { useHeaderCalculator } from '../hooks/useHeaderCalculator';
import { useRoleAccess } from '@/hooks/useRoleAccess';

const TotalsCard: React.FC<{
  transaction: Transaction;
  lines: TransactionLine[];
}> = ({ transaction, lines }) => {
  const totals = useHeaderCalculator(transaction, lines);
  const { canViewCost } = useRoleAccess();
  
  return (
    <div className="bg-white rounded-lg border p-6">
      <h3 className="font-semibold mb-4">Totals</h3>
      
      <dl className="space-y-2 text-sm">
        <Row label="Subtotal" value={totals.subtotal} />
        {totals.discount > 0 && (
          <Row label="Discount" value={-totals.discount} className="text-red-600" />
        )}
        <Row label="Taxable" value={totals.taxable} />
        <Row label="Tax" value={totals.tax} />
        {totals.shipping > 0 && (
          <Row label="Shipping" value={totals.shipping} />
        )}
        
        <div className="border-t pt-2 mt-2">
          <Row label="Total" value={totals.total} className="font-bold text-lg" />
        </div>
        
        {canViewCost && (
          <div className="border-t pt-2 mt-2 text-slate-500">
            <Row label="Cost" value={totals.cost} />
            <Row label="Margin" value={totals.margin} />
            <Row label="Margin %" value={`${totals.margin_pc.toFixed(1)}%`} />
          </div>
        )}
        
        {transaction.model_name === 'invoice' && (
          <div className="border-t pt-2 mt-2">
            <Row label="Received" value={totals.received} className="text-green-600" />
            <Row 
              label="Balance Due" 
              value={totals.balance} 
              className={totals.balance > 0 ? 'text-amber-600 font-bold' : 'text-green-600'}
            />
          </div>
        )}
      </dl>
    </div>
  );
};

const Row: React.FC<{
  label: string;
  value: number | string;
  className?: string;
}> = ({ label, value, className = '' }) => (
  <div className={`flex justify-between ${className}`}>
    <dt>{label}</dt>
    <dd>{typeof value === 'number' ? formatCurrency(value) : value}</dd>
  </div>
);
```

---

## Calculation Triggers

### Event Handlers

```typescript
// What triggers recalculation in the UI

const TransactionEditor: React.FC = () => {
  const [lines, setLines] = useState<TransactionLine[]>([]);
  const [transaction, setTransaction] = useState<Transaction>(initialTransaction);
  
  // Line quantity changed
  const handleQuantityChange = (lineId: number, quantity: number) => {
    setLines(prev => prev.map(line => 
      line.id === lineId 
        ? { ...line, quantity: { ...line.quantity, staged: quantity } }
        : line
    ));
    // Header recalculates automatically via useHeaderCalculator
  };
  
  // Line unit price changed
  const handlePriceChange = (lineId: number, unitPrice: number) => {
    setLines(prev => prev.map(line =>
      line.id === lineId
        ? { ...line, price: { ...line.price, unit: unitPrice } }
        : line
    ));
  };
  
  // Line discount changed
  const handleDiscountChange = (lineId: number, discountPc: number) => {
    setLines(prev => prev.map(line =>
      line.id === lineId
        ? { ...line, price: { ...line.price, discount_percent: discountPc } }
        : line
    ));
  };
  
  // Line added
  const handleAddLine = (newLine: TransactionLine) => {
    // Get line number from backend
    const lineNumber = await api.allocateLineNumber(transaction.id);
    setLines(prev => [...prev, { ...newLine, line_number: lineNumber }]);
  };
  
  // Line deleted (soft delete)
  const handleDeleteLine = (lineId: number) => {
    setLines(prev => prev.map(line =>
      line.id === lineId
        ? { ...line, item: { ...line.item, is_deleted: true } }
        : line
    ));
  };
  
  // Header discount changed
  const handleHeaderDiscountChange = (discount: number) => {
    setTransaction(prev => ({
      ...prev,
      totals: { ...prev.totals, discount }
    }));
  };
  
  // Tax rate changed (usually from backend lookup)
  const handleTaxRateChange = (taxRate: number) => {
    setTransaction(prev => ({
      ...prev,
      finance: { ...prev.finance, sales_tax_rate: taxRate }
    }));
  };
};
```

---

## Backend Sync

> **Important**: When syncing lines with the backend:
> - **Existing lines** (those with an `id`) must have `item_id` and `ida_item` preserved from the backend response
> - **New lines** being added will not have a line `id` until the backend assigns one on save
> - ⚠️ **Item ID Immutability**: 
>   - **R25 responsibility**: The UI must prevent users from changing `item_id` on existing lines (e.g., make item fields read-only, hide item picker on saved lines). This is the primary defense.
>   - **User guidance**: If a user attempts to change the item, display: *"To change the item, please delete this line and add a new line with the correct item."*
>   - **WC3 safeguard**: Backend validates that `item_id` hasn't changed for any existing line `id`. If violated, rejects the entire save with: `"Item_id cannot be changed for any line"`. This is a security backstop against malicious API calls.

### useTransactionSync Hook

```typescript
// src/apps/transactions/hooks/useTransactionSync.ts

import { useState, useCallback } from 'react';
import { wcapi } from '@/api/wcapi';
import type { Transaction, TransactionLine } from '../types/transactionTypes';

interface SyncResult {
  transaction: Transaction;
  lines: TransactionLine[];
  recalculated: boolean;
}

// Validate that item_id hasn't changed for existing lines
function validateLineItemIds(
  originalLines: TransactionLine[],
  modifiedLines: TransactionLine[]
): void {
  for (const modified of modifiedLines) {
    // Only check lines that have an id (existing lines)
    if (modified.id == null) continue;
    
    const original = originalLines.find(l => l.id === modified.id);
    if (original && original.item?.item_id !== modified.item?.item_id) {
      throw new Error('Item_id cannot be changed for any line');
    }
  }
}

export function useTransactionSync(originalLines: TransactionLine[]) {
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  
  const save = useCallback(async (
    transaction: Transaction,
    lines: TransactionLine[]
  ): Promise<SyncResult> => {
    setIsSyncing(true);
    setSyncError(null);
    
    try {
      // Pre-validate: reject if item_id changed on any existing line
      validateLineItemIds(originalLines, lines);
      
      // Backend recalculates and returns authoritative values
      const response = await wcapi.save({
        model_name: transaction.model_name,
        record: transaction,
        lines: lines,
      });
      
      // Check if backend values differ from frontend
      const recalculated = response.totals.total !== transaction.totals?.total;
      
      if (recalculated) {
        console.log('Backend recalculated totals:', response.totals);
      }
      
      // Backend response includes authoritative line data:
      // - Existing lines: id, item_id, ida_item preserved
      // - New lines: backend assigns id, confirms item_id/ida_item
      return {
        transaction: response.record,
        lines: response.lines,
        recalculated,
      };
    } catch (error) {
      setSyncError(error.message);
      throw error;
    } finally {
      setIsSyncing(false);
    }
  }, [originalLines]);
  
  // Preview calculation without saving
  const preview = useCallback(async (
    transaction: Transaction,
    lines: TransactionLine[]
  ): Promise<SyncResult> => {
    const response = await wcapi.calculate({
      model_name: transaction.model_name,
      record: transaction,
      lines: lines,
    });
    
    return {
      transaction: { ...transaction, totals: response.totals },
      lines: response.lines,
      recalculated: true,
    };
  }, []);
  
  return { save, preview, isSyncing, syncError };
}
```

### Sync on Save Pattern

```typescript
const TransactionDetail: React.FC = () => {
  const [transaction, setTransaction] = useState<Transaction>();
  const [lines, setLines] = useState<TransactionLine[]>([]);
  const [isDirty, setIsDirty] = useState(false);
  
  const { save, isSyncing } = useTransactionSync();
  const displayTotals = useHeaderCalculator(transaction, lines);
  
  const handleSave = async () => {
    try {
      const result = await save(transaction, lines);
      
      // Sync to backend values
      setTransaction(result.transaction);
      setLines(result.lines);
      setIsDirty(false);
      
      if (result.recalculated) {
        toast.info('Totals updated by server');
      }
      
      toast.success('Saved successfully');
    } catch (error) {
      toast.error(`Save failed: ${error.message}`);
    }
  };
  
  return (
    <div>
      {/* Show optimistic totals */}
      <TotalsCard totals={displayTotals} />
      
      <button 
        onClick={handleSave} 
        disabled={isSyncing || !isDirty}
      >
        {isSyncing ? 'Saving...' : 'Save'}
      </button>
    </div>
  );
};
```

---

## Dirty Line Tracking

> **Purpose**: Skip unchanged lines during save to improve performance and reduce unnecessary database writes.

### The `_dirty` Flag

Each line can have a `_dirty` boolean that indicates whether it needs to be saved:

| `_dirty` | Has `id` | Action on Save |
|----------|----------|----------------|
| `true` | Yes | Update existing line |
| `true` | No | Create new line |
| `false` | Yes | Skip (no database write) |
| `false` | No | Skip (ignored) |

### Tracking Dirty Lines

```typescript
interface TransactionLine {
  id?: number;          // Undefined for new lines
  _dirty: boolean;      // True if created or modified
  quantity: { qty: number };
  price: { unit: number; extended: number };
  discount: { pct: number; amt: number };
  cost?: { unit: number; extended: number; grossCost: number; discountCost: number };
  item: { item_id: string; /* ... */ };
}

// Mark dirty when line is modified
const updateLine = (index: number, changes: Partial<TransactionLine>) => {
  setLines(prev => prev.map((line, i) => 
    i === index ? { ...line, ...changes, _dirty: true } : line
  ));
};

// New lines are always dirty
const addLine = (newLine: Omit<TransactionLine, 'id' | '_dirty'>) => {
  setLines(prev => [...prev, { ...newLine, _dirty: true }]);
};
```

### Using the Transaction Save Endpoint

```typescript
const saveTransaction = async (
  modelName: string,
  record: TransactionRecord,
  lines: TransactionLine[]
) => {
  // Lines go INSIDE record.lines (consistent with /wcapi/save/ pattern)
  const payload = {
    model_name: modelName,
    record: {
      ...record,
      lines,  // <-- Lines are nested inside record
    },
    options: {
      verify_calculations: true,
      save_only_dirty: true
    }
  };

  const response = await fetch('/wcapi/transaction/save/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const error = await response.json();
    if (error.field) {
      // Calculation mismatch - log for debugging
      console.error(`Calculation mismatch on ${error.field}:`, error);
    }
    throw new Error(error.detail);
  }

  const result = await response.json();
  
  // Sync R25 totals with WC3's authoritative values
  updateTotals(result.recalculated_totals);
  
  // Clear dirty flags after successful save
  setLines(prev => prev.map(line => ({ ...line, _dirty: false })));
  
  return result;
};
```

> **Note**: Lines are provided inside `record.lines`. WC3 loops through this array 
> and processes each line based on its `_dirty` flag.
```

---

## Calculation Verification

> **WC3 verifies R25's calculations on save.** If the frontend math doesn't match within tolerance, the save is rejected.

### How It Works

```
R25 Frontend                         WC3 Backend
┌─────────────┐                     ┌─────────────┐
│ Lines with  │  POST /wcapi/       │ Verifies    │
│ _dirty flag │ ───────────────────►│ calculations│
│ + totals    │  transaction/save/  │ matches     │
└─────────────┘                     └─────────────┘
                                           │
                                    ┌──────┴──────┐
                              mismatch?      match?
                                    │             │
                              400 Error    200 + recalculated
                              with details    totals
```

### Calculation Tolerance

WC3 allows a small tolerance for floating-point precision differences:

```python
CALC_TOLERANCE = Decimal("0.01")  # $0.01 tolerance
```

This handles rounding differences between JavaScript and Python decimal math.

### Verified Fields

**Per-Line:**
- `price.extended` = qty × unit
- `discount.amt` = extended × (pct / 100)
- `cost.extended` = qty × cost.unit
- `cost.grossCost` = cost.extended (before discount)
- `cost.discountCost` = cost.extended - discount (if cost-side discount)

**Header Totals:**
- `subtotal` = Σ(line.price.extended - line.discount.amt)
- `tax` = subtotal × tax_rate
- `total` = subtotal + tax
- `margin` = subtotal - Σ(line.cost.extended)
- `margin_pct` = (margin / subtotal) × 100

### Handling Calculation Mismatches

```typescript
try {
  await saveTransaction(modelName, record, lines);
} catch (error) {
  if (error.response?.data?.field) {
    // Calculation mismatch - sync with backend and retry
    const { field, r25_value, wc3_value, line_id } = error.response.data;
    console.error(`Mismatch on ${field}: R25=${r25_value}, WC3=${wc3_value}`);
    
    // Option 1: Reload from backend
    await refetchTransaction();
    
    // Option 2: Disable verification for this save (development only)
    // await saveWithOptions({ verify_calculations: false });
  }
}
```

---

## Price Level Changes

### Backend-Triggered Recalculation

```typescript
// Price level requires backend lookup - can't calculate frontend-only

const handlePriceLevelChange = async (newPriceLevel: string) => {
  // 1. Update transaction
  setTransaction(prev => ({ ...prev, price_level: newPriceLevel }));
  
  // 2. Fetch new prices from backend
  const updatedLines = await Promise.all(
    lines.map(async (line) => {
      const priceInfo = await wcapi.priceLookup({
        item_id: line.item?.item_id,
        customer_id: transaction.customer_id,
        quantity: line.quantity?.staged,
        price_level: newPriceLevel,
      });
      
      return {
        ...line,
        price: {
          ...line.price,
          unit: priceInfo.unit_price,
          unit_base: priceInfo.list_price,
        },
      };
    })
  );
  
  // 3. Update lines with new prices
  setLines(updatedLines);
  
  // 4. Header totals recalculate automatically via hook
};
```

---

## Formatting Utilities

### Currency & Number Formatting

```typescript
// src/apps/transactions/utils/formatters.ts

export function formatCurrency(
  value: number | null | undefined,
  currency = 'USD',
  locale = 'en-US'
): string {
  if (value == null) return '--';
  
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatNumber(
  value: number | null | undefined,
  decimals = 2,
  locale = 'en-US'
): string {
  if (value == null) return '--';
  
  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatPercent(
  value: number | null | undefined,
  decimals = 1
): string {
  if (value == null) return '--';
  return `${value.toFixed(decimals)}%`;
}

export function parseNumber(input: string): number {
  // Remove currency symbols and thousands separators
  const cleaned = input.replace(/[^0-9.-]/g, '');
  return parseFloat(cleaned) || 0;
}
```

---

## Input Validation

### Numeric Input Component

```typescript
// src/apps/transactions/components/NumericInput.tsx

interface NumericInputProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  precision?: number;
  allowNegative?: boolean;
  format?: 'currency' | 'percent' | 'number';
}

export const NumericInput: React.FC<NumericInputProps> = ({
  value,
  onChange,
  min = 0,
  max,
  precision = 2,
  allowNegative = false,
  format = 'number',
}) => {
  const [displayValue, setDisplayValue] = useState(formatValue(value, format));
  const [isEditing, setIsEditing] = useState(false);
  
  const handleBlur = () => {
    setIsEditing(false);
    
    let parsed = parseNumber(displayValue);
    
    // Enforce min/max
    if (!allowNegative && parsed < 0) parsed = 0;
    if (min != null && parsed < min) parsed = min;
    if (max != null && parsed > max) parsed = max;
    
    // Round to precision
    parsed = Math.round(parsed * 10 ** precision) / 10 ** precision;
    
    onChange(parsed);
    setDisplayValue(formatValue(parsed, format));
  };
  
  return (
    <input
      type="text"
      value={isEditing ? displayValue : formatValue(value, format)}
      onChange={(e) => setDisplayValue(e.target.value)}
      onFocus={() => {
        setIsEditing(true);
        setDisplayValue(value.toString());
      }}
      onBlur={handleBlur}
      className="text-right"
    />
  );
};
```

---

## Testing Calculations

### Unit Tests

```typescript
// src/apps/transactions/utils/__tests__/lineCalculator.test.ts

import { calculateLine } from '../lineCalculator';

describe('Line Calculator', () => {
  it('calculates extended price correctly', () => {
    const result = calculateLine({
      quantity: 10,
      unitPrice: 25.00,
      discountPercent: 0,
    });
    
    expect(result.extended).toBe(250.00);
  });
  
  it('applies percentage discount', () => {
    const result = calculateLine({
      quantity: 10,
      unitPrice: 25.00,
      discountPercent: 10,
    });
    
    expect(result.discountAmount).toBe(25.00);
    expect(result.extended).toBe(225.00);
  });
  
  it('handles zero quantity', () => {
    const result = calculateLine({
      quantity: 0,
      unitPrice: 25.00,
      discountPercent: 10,
    });
    
    expect(result.extended).toBe(0);
    expect(result.discountAmount).toBe(0);
  });
  
  it('rounds to 2 decimal places', () => {
    const result = calculateLine({
      quantity: 3,
      unitPrice: 33.333,
      discountPercent: 0,
    });
    
    expect(result.extended).toBe(100.00); // Rounded from 99.999
  });
});
```

### Integration Tests

```typescript
// src/apps/transactions/__tests__/headerCalculator.test.ts

import { calculateHeaderTotals } from '../utils/headerCalculator';

describe('Header Calculator', () => {
  const mockLines = [
    { price: { extended: 100 }, cost: { extended: 60 } },
    { price: { extended: 200 }, cost: { extended: 120 } },
  ];
  
  it('calculates subtotal from lines', () => {
    const totals = calculateHeaderTotals(mockLines, 0, 0, 0);
    expect(totals.subtotal).toBe(300);
  });
  
  it('applies header discount', () => {
    const totals = calculateHeaderTotals(mockLines, 50, 0, 0);
    expect(totals.taxable).toBe(250);
  });
  
  it('calculates tax on taxable amount', () => {
    const totals = calculateHeaderTotals(mockLines, 0, 8.25, 0);
    expect(totals.tax).toBe(24.75);
  });
  
  it('includes shipping in total', () => {
    const totals = calculateHeaderTotals(mockLines, 0, 0, 25);
    expect(totals.total).toBe(325);
  });
  
  it('calculates margin correctly', () => {
    const totals = calculateHeaderTotals(mockLines, 0, 0, 0);
    expect(totals.cost).toBe(180);
    expect(totals.margin).toBe(120);
    expect(totals.margin_pc).toBeCloseTo(40, 1);
  });
});
```

---

## Multi-Currency Handling

### Currency Context

```typescript
// src/apps/transactions/context/CurrencyContext.tsx

interface CurrencySettings {
  code: string;              // EUR
  base_code: string;         // USD
  exchange_rate: number;     // 1.0856
  rate_date: string;         // When rate was locked
  symbol: string;            // €
}

const CurrencyContext = createContext<{
  currency: CurrencySettings;
  setCurrency: (currency: CurrencySettings) => void;
  convertToBase: (amount: number) => number;
  convertFromBase: (amount: number) => number;
  formatInCurrency: (amount: number) => string;
} | null>(null);

export const CurrencyProvider: React.FC<PropsWithChildren> = ({ children }) => {
  const [currency, setCurrency] = useState<CurrencySettings>({
    code: 'USD',
    base_code: 'USD',
    exchange_rate: 1,
    rate_date: new Date().toISOString().split('T')[0],
    symbol: '$',
  });
  
  const convertToBase = useCallback((amount: number) => {
    return amount * currency.exchange_rate;
  }, [currency.exchange_rate]);
  
  const convertFromBase = useCallback((amount: number) => {
    return amount / currency.exchange_rate;
  }, [currency.exchange_rate]);
  
  const formatInCurrency = useCallback((amount: number) => {
    return formatCurrency(amount, currency.code);
  }, [currency.code]);
  
  return (
    <CurrencyContext.Provider value={{
      currency,
      setCurrency,
      convertToBase,
      convertFromBase,
      formatInCurrency,
    }}>
      {children}
    </CurrencyContext.Provider>
  );
};
```

### Multi-Currency Display

```typescript
// Show both currencies when transaction is in foreign currency
const AmountDisplay: React.FC<{ amount: number }> = ({ amount }) => {
  const { currency, convertToBase, formatInCurrency } = useCurrency();
  
  const isMultiCurrency = currency.code !== currency.base_code;
  
  return (
    <div>
      <span className="font-semibold">{formatInCurrency(amount)}</span>
      {isMultiCurrency && (
        <span className="text-gray-500 text-sm ml-2">
          ({formatCurrency(convertToBase(amount), currency.base_code)})
        </span>
      )}
    </div>
  );
};
```

---

## Blanket Orders & Releases

### Blanket Order UI

```typescript
interface BlanketLineDisplay {
  line: TransactionLine;
  blanket_qty: number;
  released_qty: number;
  remaining_qty: number;
}

const BlanketLineRow: React.FC<{ line: BlanketLineDisplay }> = ({ line }) => {
  const remainingPct = (line.remaining_qty / line.blanket_qty) * 100;
  
  return (
    <tr>
      <td>{line.line.item?.ida_item}</td>
      <td className="text-right">{formatNumber(line.blanket_qty, 0)}</td>
      <td className="text-right">{formatNumber(line.released_qty, 0)}</td>
      <td className="text-right font-semibold">{formatNumber(line.remaining_qty, 0)}</td>
      <td>
        <div className="w-full bg-gray-200 rounded h-2">
          <div 
            className="bg-blue-600 h-2 rounded" 
            style={{ width: `${100 - remainingPct}%` }}
          />
        </div>
      </td>
    </tr>
  );
};
```

### Release Creation Modal

```typescript
const CreateReleaseModal: React.FC<{
  blanketOrder: Transaction;
  onRelease: (lines: ReleaseLineSpec[]) => void;
}> = ({ blanketOrder, onRelease }) => {
  const [releaseLines, setReleaseLines] = useState<ReleaseLineSpec[]>([]);
  
  const handleQuantityChange = (lineId: number, qty: number) => {
    const blanketLine = blanketOrder.lines.find(l => l.id === lineId);
    const maxQty = blanketLine?.quantity?.remaining_qty ?? 0;
    
    setReleaseLines(prev => {
      const existing = prev.find(r => r.blanket_line_id === lineId);
      if (existing) {
        return prev.map(r => 
          r.blanket_line_id === lineId 
            ? { ...r, quantity: Math.min(qty, maxQty) }
            : r
        );
      }
      return [...prev, { blanket_line_id: lineId, quantity: Math.min(qty, maxQty) }];
    });
  };
  
  return (
    <Modal title="Create Release Order">
      {blanketOrder.lines.map(line => (
        <div key={line.id} className="flex items-center gap-4">
          <span>{line.item?.ida_item}</span>
          <span className="text-gray-500">
            Available: {formatNumber(line.quantity?.remaining_qty ?? 0, 0)}
          </span>
          <NumericInput
            value={releaseLines.find(r => r.blanket_line_id === line.id)?.quantity ?? 0}
            onChange={(qty) => handleQuantityChange(line.id, qty)}
            max={line.quantity?.remaining_qty ?? 0}
            precision={0}
          />
        </div>
      ))}
      <Button onClick={() => onRelease(releaseLines)}>Create Release</Button>
    </Modal>
  );
};
```

---

## Bundle & Kit Pricing

### Bundle Line Display

```typescript
interface BundleComponent {
  item_id: number;
  ida_item: string;
  quantity: number;
  unit_price: number;
  extended: number;
  included: boolean;
}

const BundleLineCard: React.FC<{ 
  line: TransactionLine;
  onComponentToggle: (componentId: number, included: boolean) => void;
}> = ({ line, onComponentToggle }) => {
  const components = line.components ?? [];
  const isConfigurable = line.item?.bundle_type === 'configurable';
  
  const componentTotal = useMemo(() => 
    components
      .filter(c => c.included)
      .reduce((sum, c) => sum + c.extended, 0),
    [components]
  );
  
  const bundleSavings = componentTotal - (line.price?.bundle_price ?? 0);
  
  return (
    <Card>
      <div className="font-semibold">{line.item?.description1}</div>
      <div className="text-sm text-gray-500">Bundle includes:</div>
      
      <div className="ml-4 mt-2 space-y-1">
        {components.map(comp => (
          <div key={comp.item_id} className="flex items-center gap-2">
            {isConfigurable && (
              <Checkbox
                checked={comp.included}
                onChange={(checked) => onComponentToggle(comp.item_id, checked)}
              />
            )}
            <span>{comp.ida_item}</span>
            <span className="text-gray-500">× {comp.quantity}</span>
            <span className="ml-auto">{formatCurrency(comp.extended)}</span>
          </div>
        ))}
      </div>
      
      <div className="mt-4 pt-2 border-t flex justify-between">
        <span className="text-gray-500 line-through">
          {formatCurrency(componentTotal)}
        </span>
        <span className="font-semibold text-green-600">
          Bundle Price: {formatCurrency(line.price?.bundle_price ?? 0)}
        </span>
        <span className="text-sm text-green-600">
          Save {formatCurrency(bundleSavings)}
        </span>
      </div>
    </Card>
  );
};
```

---

## Tiered Pricing Display

### Price Break Table

```typescript
interface PriceTier {
  min_qty: number;
  max_qty: number | null;
  price: number;
}

const PriceBreakTable: React.FC<{
  tiers: PriceTier[];
  currentQty: number;
}> = ({ tiers, currentQty }) => {
  const currentTier = tiers.find(t => 
    currentQty >= t.min_qty && (t.max_qty === null || currentQty <= t.max_qty)
  );
  
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b">
          <th className="text-left">Quantity</th>
          <th className="text-right">Unit Price</th>
        </tr>
      </thead>
      <tbody>
        {tiers.map((tier, idx) => {
          const isActive = tier === currentTier;
          return (
            <tr 
              key={idx}
              className={isActive ? 'bg-blue-50 font-semibold' : ''}
            >
              <td>
                {tier.max_qty 
                  ? `${tier.min_qty} - ${tier.max_qty}`
                  : `${tier.min_qty}+`
                }
              </td>
              <td className="text-right">{formatCurrency(tier.price)}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
};
```

### Next Price Break Prompt

```typescript
const NextBreakPrompt: React.FC<{
  tiers: PriceTier[];
  currentQty: number;
  unitPrice: number;
}> = ({ tiers, currentQty, unitPrice }) => {
  // Find next tier
  const nextTier = tiers.find(t => t.min_qty > currentQty);
  
  if (!nextTier) return null;
  
  const qtyNeeded = nextTier.min_qty - currentQty;
  const priceDrop = unitPrice - nextTier.price;
  const totalSavings = (currentQty + qtyNeeded) * priceDrop;
  
  return (
    <div className="text-sm text-blue-600 mt-1">
      💡 Add {qtyNeeded} more for {formatCurrency(nextTier.price)}/ea
      (save {formatCurrency(totalSavings)} total)
    </div>
  );
};
```

---

## Promo Code Input

### Promo Code Field

```typescript
const PromoCodeInput: React.FC<{
  onApply: (code: string) => Promise<PromoValidation>;
  appliedPromos: AppliedPromo[];
  onRemove: (code: string) => void;
}> = ({ onApply, appliedPromos, onRemove }) => {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const handleApply = async () => {
    if (!code.trim()) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await onApply(code.trim().toUpperCase());
      if (!result.valid) {
        setError(result.error ?? 'Invalid promo code');
      } else {
        setCode('');
      }
    } catch (e) {
      setError('Failed to validate promo code');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div>
      <div className="flex gap-2">
        <input
          type="text"
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          placeholder="Enter promo code"
          className="border rounded px-3 py-1"
        />
        <Button onClick={handleApply} disabled={loading}>
          {loading ? 'Checking...' : 'Apply'}
        </Button>
      </div>
      
      {error && (
        <div className="text-red-600 text-sm mt-1">{error}</div>
      )}
      
      {appliedPromos.length > 0 && (
        <div className="mt-2 space-y-1">
          {appliedPromos.map(promo => (
            <div key={promo.code} className="flex items-center gap-2 text-green-600">
              <CheckIcon className="h-4 w-4" />
              <span>{promo.code}</span>
              <span className="text-gray-500">- {promo.description}</span>
              <button 
                onClick={() => onRemove(promo.code)}
                className="text-red-600 hover:underline text-sm"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
```

---

## Credit Limit Display

### Credit Status Badge

```typescript
interface CreditStatus {
  credit_limit: number;
  available_credit: number;
  open_balance: number;
  credit_hold: boolean;
  utilization_pc: number;
}

const CreditStatusBadge: React.FC<{ status: CreditStatus }> = ({ status }) => {
  const getStatusColor = () => {
    if (status.credit_hold) return 'bg-red-100 text-red-800';
    if (status.utilization_pc > 90) return 'bg-yellow-100 text-yellow-800';
    if (status.utilization_pc > 75) return 'bg-orange-100 text-orange-800';
    return 'bg-green-100 text-green-800';
  };
  
  return (
    <div className={`rounded px-3 py-2 ${getStatusColor()}`}>
      {status.credit_hold ? (
        <div className="font-semibold">⚠️ Credit Hold</div>
      ) : (
        <>
          <div className="text-sm">Credit Available</div>
          <div className="font-semibold">{formatCurrency(status.available_credit)}</div>
          <div className="text-xs mt-1">
            {status.utilization_pc.toFixed(0)}% of {formatCurrency(status.credit_limit)} used
          </div>
        </>
      )}
    </div>
  );
};
```

### Order Credit Warning

```typescript
const OrderCreditWarning: React.FC<{
  orderTotal: number;
  availableCredit: number;
}> = ({ orderTotal, availableCredit }) => {
  const willExceed = orderTotal > availableCredit;
  const overAmount = orderTotal - availableCredit;
  
  if (!willExceed) return null;
  
  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded p-4">
      <div className="font-semibold text-yellow-800">
        ⚠️ Order exceeds available credit by {formatCurrency(overAmount)}
      </div>
      <div className="text-sm text-yellow-700 mt-1">
        This order will require credit approval before processing.
      </div>
    </div>
  );
};
```

---

## Approval Workflow UI

### Approval Status Banner

```typescript
interface ApprovalRequest {
  id: number;
  trigger: string;
  message: string;
  status: 'pending' | 'approved' | 'rejected';
  requested_at: string;
  decided_at?: string;
  decided_by?: string;
}

const ApprovalStatusBanner: React.FC<{
  approvals: ApprovalRequest[];
}> = ({ approvals }) => {
  const pendingApprovals = approvals.filter(a => a.status === 'pending');
  const rejectedApprovals = approvals.filter(a => a.status === 'rejected');
  
  if (pendingApprovals.length > 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="font-semibold text-yellow-800 flex items-center gap-2">
          <ClockIcon className="h-5 w-5" />
          Pending Approval
        </div>
        <ul className="mt-2 space-y-1">
          {pendingApprovals.map(approval => (
            <li key={approval.id} className="text-sm text-yellow-700">
              • {approval.message}
            </li>
          ))}
        </ul>
      </div>
    );
  }
  
  if (rejectedApprovals.length > 0) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="font-semibold text-red-800 flex items-center gap-2">
          <XCircleIcon className="h-5 w-5" />
          Approval Rejected
        </div>
        <ul className="mt-2 space-y-1">
          {rejectedApprovals.map(approval => (
            <li key={approval.id} className="text-sm text-red-700">
              • {approval.message}
              {approval.decided_by && (
                <span className="text-gray-500"> - by {approval.decided_by}</span>
              )}
            </li>
          ))}
        </ul>
      </div>
    );
  }
  
  return null;
};
```

---

## Partial Payment Display

### Payment Progress

```typescript
const PaymentProgress: React.FC<{
  total: number;
  received: number;
  balance: number;
}> = ({ total, received, balance }) => {
  const paidPct = (received / total) * 100;
  
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span>Paid: {formatCurrency(received)}</span>
        <span>Balance: {formatCurrency(balance)}</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-3">
        <div 
          className={`h-3 rounded-full ${
            paidPct >= 100 ? 'bg-green-500' : 'bg-blue-500'
          }`}
          style={{ width: `${Math.min(paidPct, 100)}%` }}
        />
      </div>
      <div className="text-center text-sm text-gray-500">
        {paidPct.toFixed(0)}% paid
      </div>
    </div>
  );
};
```

### Payment History Table

```typescript
const PaymentHistory: React.FC<{ payments: Payment[] }> = ({ payments }) => {
  return (
    <table className="w-full">
      <thead>
        <tr className="border-b text-left">
          <th className="pb-2">Date</th>
          <th className="pb-2">Method</th>
          <th className="pb-2 text-right">Amount</th>
        </tr>
      </thead>
      <tbody>
        {payments.map(payment => (
          <tr key={payment.id} className="border-b">
            <td className="py-2">{formatDate(payment.payment_date)}</td>
            <td className="py-2">{payment.method}</td>
            <td className="py-2 text-right font-semibold">
              {formatCurrency(payment.amount)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};
```

---

## Refund/Credit Memo UI

### Return Line Selector

```typescript
const ReturnLineSelector: React.FC<{
  invoiceLines: TransactionLine[];
  onSelectReturn: (lines: ReturnLineSpec[]) => void;
}> = ({ invoiceLines, onSelectReturn }) => {
  const [returnQtys, setReturnQtys] = useState<Record<number, number>>({});
  
  const handleQtyChange = (lineId: number, qty: number) => {
    const line = invoiceLines.find(l => l.id === lineId);
    const maxQty = (line?.quantity?.staged ?? 0) - (line?.quantity?.returned ?? 0);
    
    setReturnQtys(prev => ({
      ...prev,
      [lineId]: Math.min(Math.max(0, qty), maxQty),
    }));
  };
  
  const returnTotal = useMemo(() => {
    return invoiceLines.reduce((sum, line) => {
      const returnQty = returnQtys[line.id] ?? 0;
      if (returnQty === 0) return sum;
      
      const unitPrice = (line.price?.extended ?? 0) / (line.quantity?.staged ?? 1);
      return sum + (returnQty * unitPrice);
    }, 0);
  }, [invoiceLines, returnQtys]);
  
  const handleSubmit = () => {
    const specs = Object.entries(returnQtys)
      .filter(([_, qty]) => qty > 0)
      .map(([lineId, quantity]) => ({ line_id: Number(lineId), quantity }));
    onSelectReturn(specs);
  };
  
  return (
    <div>
      {invoiceLines.map(line => (
        <div key={line.id} className="flex items-center gap-4 py-2 border-b">
          <span className="flex-1">{line.item?.description1}</span>
          <span className="text-gray-500">
            Max: {(line.quantity?.staged ?? 0) - (line.quantity?.returned ?? 0)}
          </span>
          <NumericInput
            value={returnQtys[line.id] ?? 0}
            onChange={(qty) => handleQtyChange(line.id, qty)}
            precision={0}
          />
        </div>
      ))}
      
      <div className="mt-4 pt-4 border-t flex justify-between items-center">
        <span className="font-semibold">Credit Amount: {formatCurrency(returnTotal)}</span>
        <Button onClick={handleSubmit} disabled={returnTotal === 0}>
          Create Credit Memo
        </Button>
      </div>
    </div>
  );
};
```

---

## Performance Patterns

### Debounced Input Updates

```typescript
import { useDebouncedCallback } from 'use-debounce';

const DebouncedQuantityInput: React.FC<{
  value: number;
  onChange: (value: number) => void;
}> = ({ value, onChange }) => {
  const [localValue, setLocalValue] = useState(value);
  
  // Sync local value when prop changes
  useEffect(() => {
    setLocalValue(value);
  }, [value]);
  
  // Debounce updates to parent
  const debouncedOnChange = useDebouncedCallback(
    (newValue: number) => onChange(newValue),
    300
  );
  
  const handleChange = (newValue: number) => {
    setLocalValue(newValue);       // Immediate local update
    debouncedOnChange(newValue);   // Debounced parent update
  };
  
  return (
    <input
      type="number"
      value={localValue}
      onChange={(e) => handleChange(Number(e.target.value))}
    />
  );
};
```

### Memoized Calculations

```typescript
const TransactionTotalsCard: React.FC<{ lines: TransactionLine[] }> = ({ lines }) => {
  // Only recalculate when lines change
  const totals = useMemo(() => calculateHeaderTotals(lines), [lines]);
  
  // Memoize expensive line calculations
  const lineMetrics = useMemo(() => 
    lines.map(line => ({
      id: line.id,
      margin: calculateLineMargin(line),
      marginPct: calculateLineMarginPct(line),
    })),
    [lines]
  );
  
  return <TotalsDisplay totals={totals} lineMetrics={lineMetrics} />;
};
```

---

## Error Handling

### Calculation Error Recovery

```typescript
const useTransactionWithFallback = (transactionId: number) => {
  const [calcError, setCalcError] = useState<string | null>(null);
  
  const saveTransaction = async (data: Transaction, lines: TransactionLine[]) => {
    try {
      const result = await wcapi.save({
        model_name: 'invoice',
        record: data,
        lines,
      });
      setCalcError(null);
      return result;
      
    } catch (error: any) {
      if (error.code === 'CALCULATION_ERROR') {
        // Show warning but allow save with frontend calcs
        setCalcError('Server calculation unavailable. Using estimated totals.');
        
        return await wcapi.save({
          model_name: 'invoice',
          record: data,
          lines,
          skip_recalc: true,
        });
      }
      throw error;
    }
  };
  
  return { saveTransaction, calcError };
};
```

### Validation Display

```typescript
const ValidationErrors: React.FC<{
  errors: CalculationError[];
}> = ({ errors }) => {
  if (errors.length === 0) return null;
  
  return (
    <div className="bg-red-50 border border-red-200 rounded p-4">
      <div className="font-semibold text-red-800">Calculation Issues</div>
      <ul className="mt-2 space-y-1">
        {errors.map((error, idx) => (
          <li key={idx} className="text-sm text-red-700">
            {error.line_id && `Line ${error.line_id}: `}
            {error.message}
          </li>
        ))}
      </ul>
    </div>
  );
};
```

---

## Related Files

- [transactionTypes.ts](../src/apps/transactions/types/transactionTypes.ts) - TypeScript interfaces
- [TransactionDetailBase.tsx](../src/apps/transactions/components/TransactionDetailBase.tsx) - Base detail component
- [FinancialsCard.tsx](../src/apps/transactions/components/FinancialsCard.tsx) - Totals display

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-14 | 1.0 | Initial document |
| 2026-01-14 | 1.1 | Added multi-currency, blanket orders, bundles, tiered pricing, promo codes, credit limits, approvals, partial payments, refunds, performance patterns, error handling |
