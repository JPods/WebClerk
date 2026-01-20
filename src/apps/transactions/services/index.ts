/**
 * Transaction Services - Single Point of Authority exports
 * 
 * Each service provides centralized logic for a specific transaction behavior.
 * Import services from this index for clean imports.
 */

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

// Re-export default
export { default as LineItemService } from './lineItemService';
