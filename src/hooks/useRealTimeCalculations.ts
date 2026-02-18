/**
 * useRealTimeCalculations — WC3-aligned real-time totals hook
 *
 * Mirrors the backend's `compute_*_sell_cost_totals()` services so the UI
 * can display optimistic totals while editing lines, before the server
 * persists them.
 *
 * Backend reference:
 *   apps/transactions/services/order_totals.py
 *   apps/transactions/services/proposal_totals.py
 *   apps/transactions/services/invoice_totals.py
 *   apps/transactions/services/purchase_totals.py
 *
 * @see webClerk3/readmes/topics/transactions/transactions-totals.md §3
 */
import { useMemo } from 'react';
import {
  computeHeaderTotals,
  type HeaderTotalsResult,
} from '../apps/transactions/services/headerTotals';
import type {
  TransactionLine,
  TransactionTotals,
  HeaderCost,
  HeaderSell,
} from '../apps/transactions/types/transactionTypes';

// Re-export the canonical types so existing consumers keep working.
export type { TransactionTotals, HeaderCost, HeaderSell };

/**
 * Compute sell / cost / totals envelopes from an array of TransactionLine
 * objects each time lines, transactionType, or received changes.
 *
 * @param lines - The current (possibly unsaved) line array.
 * @param transactionType - 'order' | 'proposal' | 'invoice' | 'purchase' | 'workorder'.
 * @param received - Payment amount already received (preserved through recalc).
 * @returns `{ sell, cost, totals }` — same three-envelope shape the server returns.
 */
export function useRealTimeCalculations(
  lines: TransactionLine[],
  transactionType = 'order',
  received: number | null = null,
): HeaderTotalsResult {
  return useMemo(
    () => computeHeaderTotals(lines, { transactionType, received }),
    [lines, transactionType, received],
  );
}