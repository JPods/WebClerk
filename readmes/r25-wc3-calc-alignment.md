# R25 ↔ WC3 Calculation Alignment

> How the React 2025 frontend mirrors the WebClerk 3 Django backend's
> transaction-totals logic so that both sides produce **identical** numbers.

---

## 1. Architecture Overview

```
WC3 (Django / Python Decimal)         R25 (React / TypeScript number)
──────────────────────────────         ─────────────────────────────────
base_line_model._calculate_            LineItemService.calculateLine()
  extended_price()                       ↳ calculationUtils.round()

compute_order_sell_cost_totals()       computeHeaderTotals()
compute_po_sell_cost_totals()            • headerTotals.ts
  ↳ order_totals.py                      • uses same field names
  ↳ po_totals.py                         • same aggregation logic

Signal auto-recalc (post_save)         useRealTimeCalculations() hook
                                         ↳ wraps computeHeaderTotals
                                           with useMemo
```

## 2. File Map

| WC3 Backend File | R25 Frontend File | Purpose |
|---|---|---|
| `apps/orders/services/order_totals.py` | `src/apps/transactions/services/headerTotals.ts` | Header-level totals rollup |
| `apps/orders/services/po_totals.py` | (same file, exec-side branch) | PO / exec totals |
| `apps/orders/models/base_line_model.py` | `src/apps/transactions/services/lineItemService.ts` | Line-level extended price |
| `_to_decimal()` helper | `src/apps/transactions/services/calculationUtils.ts` | Rounding / coercion |
| — | `src/hooks/useRealTimeCalculations.ts` | React hook wrapping `computeHeaderTotals` |
| — | `src/components/transactions/common/TransactionTotals.tsx` | Display component |
| — | `src/apps/common/components/panels/FinancialsPanel.tsx` | Detailed financials panel |

## 3. Shared Formulas

### 3.1 Line-level (per line item)

```
price.extended = round(qty_staged × price.unit_price − discount_amount, precision)
cost.extended  = round(qty_staged × cost.unit_cost   − cost_discount,   cost_precision)
```

**Discount logic** (must match on both sides):
- If explicit `discount_amount > 0` → use it directly
- Else if `discount_percent > 0` → `discount_amount = gross × (discount_percent / 100)`
- Else → `discount_amount = 0`

**Precision**: read from `line.price.precision` / `line.cost.precision` (default: 2).

### 3.2 Header-level (aggregated from lines)

Soft-deleted lines (`is_deleted === true`) are **always skipped**.

#### Sell envelope (sales-side transactions only)

```
sell.line_sum_goods = Σ line.price.extended
sell.discount       = Σ line.price.discount_amount
sell.total          = sell.line_sum_goods
```

#### Cost envelope (all transaction types)

```
cost.line_sum_goods    = Σ line.cost.extended
cost.line_sum_tax      = Σ line.cost.tax
cost.line_sum_shipping = Σ line.cost.shipping
cost.line_sum_handling = Σ line.cost.handling
cost.freight           = Σ line.cost.freight
cost.commissions       = Σ line.cost.commissions
cost.total             = line_sum_goods + line_sum_tax + line_sum_shipping
                         + line_sum_handling + freight + commissions
```

#### Totals envelope

```
totals.total     = sell.total  (sales-side)  OR  cost.total (exec-side)
totals.cost      = cost.total
totals.margin    = totals.total − totals.cost
totals.margin_pc = totals.total > 0
                   ? (totals.margin / totals.total) × 100
                   : null
totals.balance   = totals.total − (totals.received ?? 0)
```

## 4. JSON Envelope Shape

Both WC3 API responses and R25 in-memory state use the same three-envelope
structure. The TypeScript interfaces live in `transactionTypes.ts`:

```typescript
interface HeaderSell {
  line_sum_goods?: number | null;
  discount?: number | null;
  tax?: number | null;
  shipping?: number | null;
  handling?: number | null;
  other?: number | null;
  total?: number | null;
}

interface HeaderCost {
  line_sum_goods?: number | null;
  line_sum_tax?: number | null;
  line_sum_shipping?: number | null;
  line_sum_handling?: number | null;
  handling?: number | null;
  freight?: number | null;
  tax_rate?: number | null;
  tax?: number | null;
  commissions?: number | null;
  total?: number | null;
}

interface TransactionTotals {
  subtotal?: number | null;
  discount?: number | null;
  taxable?: number | null;
  tax?: number | null;
  shipping?: number | null;
  other?: number | null;
  total?: number | null;
  cost?: number | null;
  margin?: number | null;
  margin_pc?: number | null;
  received?: number | null;
  balance?: number | null;
}
```

## 5. Transaction Type Classification

| Type | Side | Has sell envelope? |
|---|---|---|
| Order, Proposal, Invoice, Quote, Credit Note | Sales | Yes |
| Purchase Order, Bill, Work Order, Transfer | Exec | No — `totals.total = cost.total` |

Helper functions: `isSalesTransaction(type)` / `isExecTransaction(type)`.

## 6. Testing

Tests live at:

```
src/apps/transactions/services/__tests__/wc3CalcAlignment.test.ts
```

Run with:

```bash
npx vitest run src/apps/transactions/services/__tests__/wc3CalcAlignment.test.ts
```

27 tests cover:
- `round()`, `toNumber()`, `formatCurrency()`, `formatPercent()`
- `LineItemService.calculateLine()` — precision-aware, discount logic
- `computeHeaderTotals()` — sell+cost aggregation, soft-delete, exec-side, balance
- `computeCostOnlyTotals()` — flat cost dict
- Default envelopes — WC3 key presence
- Transaction type helpers

## 7. When Backend Formulas Change

If WC3 modifies its totals logic:

1. Update `headerTotals.ts` `computeHeaderTotals()` to match
2. Update `lineItemService.ts` `calculateLine()` if line formula changes
3. Update type interfaces in `transactionTypes.ts` if envelope shape changes
4. Run the alignment test suite to verify
5. Update this document

## 8. Key Design Decisions

| Decision | Rationale |
|---|---|
| Pure functions (not hooks) for core math | Usable in services, workers, and components |
| `useMemo`-based hook wrapper | React-friendly without re-render churn |
| `number` not `Decimal` | JS has no native Decimal; `round()` compensates |
| Field names match WC3 JSON exactly | Zero-translation between API response and display |
| Precision per-line, not global | WC3 stores precision on each line's price/cost envelope |
