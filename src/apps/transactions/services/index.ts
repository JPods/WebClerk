/**
 * Transaction Services - Single Point of Authority exports
 * 
 * Each service provides centralized logic for a specific transaction behavior.
 * Import services from this index for clean imports.
 */

// Calculation Utilities (shared rounding, formatting)
export {
  round,
  toNumber,
  formatCurrency,
  formatPercent,
  formatNumber,
} from './calculationUtils';

// Line Item Service
export {
  LineItemService,
  createSalesLineItemService,
  createPurchaseLineItemService,
  addItemToLines,
  updateLineInArray,
  removeLineFromArray,
  getActiveLines,
  isSalesTransaction,
  isExecTransaction,
  type TransactionType,
  type LineItemServiceConfig,
  type AddItemOptions,
  type LineCalculation,
} from './lineItemService';

// Header Totals Rollup (mirrors WC3 compute_*_sell_cost_totals)
export {
  computeHeaderTotals,
  computeCostOnlyTotals,
  defaultSell,
  defaultCost,
  defaultTotals,
  type HeaderTotalsResult,
  type ComputeTotalsOptions,
} from './headerTotals';

// Re-export default
export { default as LineItemService } from './lineItemService';
