/**
 * Header Totals Service — client-side mirror of WC3 backend totals rollup
 *
 * Implements the same aggregation that the WC3 Django services perform when
 * `update_sell_cost_totals(persist=True)` is called on a header model.
 *
 * Backend reference files:
 *   apps/transactions/services/order_totals.py     — compute_order_sell_cost_totals()
 *   apps/transactions/services/proposal_totals.py  — compute_proposal_sell_cost_totals()
 *   apps/transactions/services/invoice_totals.py   — compute_invoice_sell_cost_totals()
 *   apps/transactions/services/purchase_totals.py  — compute_purchase_sell_cost_totals()
 *   apps/transactions/services/po_totals.py        — compute_purchase_cost_totals()
 *
 * Formulae:
 *   SELL SIDE (order, proposal, invoice):
 *     sell.line_sum_goods   = Σ line.price.extended
 *     sell.discount         = Σ line.price.discount_amount
 *     sell.total            = sell.line_sum_goods
 *
 *     cost.line_sum_goods   = Σ line.cost.extended
 *     cost.line_sum_tax     = Σ line.cost.tax
 *     cost.line_sum_shipping= Σ line.cost.shipping
 *     cost.line_sum_handling= Σ line.cost.handling
 *     cost.freight          = Σ line.cost.freight
 *     cost.commissions      = Σ line.cost.commissions
 *     cost.total            = goods + tax + shipping + handling + freight + commissions
 *
 *     totals.total     = sell.total
 *     totals.cost      = cost.total
 *     totals.margin    = sell.total − cost.total
 *     totals.margin_pc = (margin / sell.total) × 100   if sell.total > 0
 *     totals.received  = (preserved from existing header value)
 *     totals.balance   = totals.total − totals.received
 *
 *   EXEC SIDE (purchase, workorder):
 *     No sell envelope.
 *     totals.total = cost.total
 *
 * @see webClerk3/readmes/topics/transactions/transactions-totals.md §3
 */

import { round, toNumber } from './calculationUtils';
import { isSalesTransaction } from './lineItemService';
import type {
  TransactionLine,
  TransactionTotals,
  HeaderCost,
  HeaderSell,
} from '../types/transactionTypes';

// ============================================================================
// Types
// ============================================================================

/** The three-envelope shape returned by WC3 compute_*_sell_cost_totals(). */
export interface HeaderTotalsResult {
  sell: HeaderSell;
  cost: HeaderCost;
  totals: TransactionTotals;
}

export interface ComputeTotalsOptions {
  /** Transaction type — determines sell-side vs exec-side logic. */
  transactionType: string;
  /** Previously received amount, preserved through recalc. */
  received?: number | null;
}

// ============================================================================
// Default (empty) envelopes
// ============================================================================

export function defaultSell(): HeaderSell {
  return {
    line_sum_goods: 0,
    discount: 0,
    tax: 0,
    shipping: 0,
    handling: 0,
    other: 0,
    total: 0,
  };
}

export function defaultCost(): HeaderCost {
  return {
    line_sum_goods: 0,
    line_sum_tax: 0,
    line_sum_shipping: 0,
    line_sum_handling: 0,
    freight: 0,
    commissions: 0,
    tax_rate: null,
    tax: 0,
    total: 0,
  };
}

export function defaultTotals(): TransactionTotals {
  return {
    total: 0,
    cost: 0,
    margin: 0,
    margin_pc: 0,
    received: 0,
    balance: 0,
  };
}

// ============================================================================
// Core rollup function
// ============================================================================

/**
 * Compute sell, cost, and totals envelopes from an array of lines.
 *
 * This is the client-side equivalent of WC3's
 * `compute_order_sell_cost_totals()` (and the proposal/invoice/purchase
 * variants which share the same logic).
 *
 * Lines whose `item.is_deleted` flag is true are excluded.
 *
 * @param lines - Array of TransactionLine records from the API or local state.
 * @param options - Transaction type and any preserved values (received, etc.).
 * @returns The three-envelope `{ sell, cost, totals }` shape.
 */
export function computeHeaderTotals(
  lines: TransactionLine[],
  options: ComputeTotalsOptions,
): HeaderTotalsResult {
  const isSales = isSalesTransaction(options.transactionType);

  // Accumulators
  let sellGoods = 0;
  let sellDiscount = 0;

  let costGoods = 0;
  let costTax = 0;
  let costShipping = 0;
  let costHandling = 0;
  let costFreight = 0;
  let costCommissions = 0;

  // --- Iterate active lines ---
  for (const ln of lines) {
    // Skip soft-deleted lines (mirrors Django queryset filter)
    const item = ln.item as Record<string, unknown> | undefined;
    if (item?.is_deleted) continue;

    const p = (ln.price ?? {}) as Record<string, unknown>;
    const c = (ln.cost ?? {}) as Record<string, unknown>;

    // Sell aggregation (sales-side only)
    if (isSales) {
      sellGoods += toNumber(p.extended);
      sellDiscount += toNumber(p.discount_amount);
    }

    // Cost aggregation (all transaction types)
    costGoods += toNumber(c.extended);
    costTax += toNumber(c.tax);
    costShipping += toNumber(c.shipping);
    costHandling += toNumber(c.handling);
    costFreight += toNumber(c.freight);
    costCommissions += toNumber(c.commissions);
  }

  // --- Build sell envelope ---
  const sell: HeaderSell = {
    line_sum_goods: round(sellGoods),
    discount: round(sellDiscount),
    tax: 0,
    shipping: 0,
    handling: 0,
    other: 0,
    total: round(sellGoods),
  };

  // --- Build cost envelope ---
  const costTotal = round(
    costGoods + costTax + costShipping + costHandling + costFreight + costCommissions,
  );
  const cost: HeaderCost = {
    line_sum_goods: round(costGoods),
    line_sum_tax: round(costTax),
    line_sum_shipping: round(costShipping),
    line_sum_handling: round(costHandling),
    freight: round(costFreight),
    commissions: round(costCommissions),
    tax_rate: null,
    tax: round(costTax),
    total: costTotal,
  };

  // --- Build totals envelope ---
  const totalAmt = isSales ? round(sellGoods) : costTotal;
  const margin = round(totalAmt - costTotal);
  const marginPc = totalAmt > 0 ? round((margin / totalAmt) * 100, 2) : null;
  const received = toNumber(options.received, 0);
  const balance = round(totalAmt - received);

  const totals: TransactionTotals = {
    total: totalAmt,
    cost: costTotal,
    margin,
    margin_pc: marginPc,
    received: received || null,
    balance,
  };

  return { sell, cost, totals };
}

// ============================================================================
// Exec-side cost-only rollup  (mirrors po_totals.py)
// ============================================================================

/**
 * Compute cost-only rollup for purchase/workorder (no sell envelope).
 *
 * Identical to `computeHeaderTotals` with `transactionType='purchase'`,
 * but returns only the flat cost dict — matching WC3's
 * `compute_purchase_cost_totals()`.
 */
export function computeCostOnlyTotals(
  lines: TransactionLine[],
): HeaderCost {
  const result = computeHeaderTotals(lines, { transactionType: 'purchase' });
  return result.cost;
}
