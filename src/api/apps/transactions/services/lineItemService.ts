/**
 * Line Item Service - Single Point of Authority for transaction line management
 * 
 * Handles adding, updating, and managing transaction line items across all
 * transaction types (sales_order, proposal, invoice, purchase_order, work_order).
 * 
 * Key behaviors:
 * - Sales transactions: price.unit is the primary value
 * - Purchase transactions: cost.unit is the primary value
 */

import { wcapi } from '../../../wcapi';
import type { TransactionLine } from '../types/transactionTypes';
import {
  ItemSearchResult,
  resolveItemCode,
  resolveItemDescription,
  resolveUnitPrice,
  resolveUnitCost,
} from '../components/TransactionItemSearch';

// ============================================================================
// Types
// ============================================================================

export type TransactionType = 'sales_order' | 'proposal' | 'invoice' | 'purchase_order' | 'work_order';

export interface LineItemServiceConfig {
  transactionType: TransactionType;
  useCost: boolean;  // false for sales, true for purchase
  priceField: 'price' | 'cost';
}

export interface AddItemOptions {
  quantity?: number;
  unitPrice?: number;
  unitCost?: number;
  priceLevel?: string;
  discountPercent?: number;
}

export interface LineCalculation {
  gross: number;
  discountAmount: number;
  extended: number;
  grossCost: number;
  discountCost: number;
  costExtended: number;
  margin: number;
  marginPc: number;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Determine if a transaction type is sales-side (uses price as primary)
 */
export function isSalesTransaction(transactionType: string): boolean {
  const kind = transactionType.toLowerCase().replace(/-/g, '_');
  return ['sales_order', 'salesorder', 'order', 'proposal', 'invoice'].includes(kind);
}

/**
 * Determine if a transaction type is exec-side (uses cost as primary)
 */
export function isExecTransaction(transactionType: string): boolean {
  const kind = transactionType.toLowerCase().replace(/-/g, '_');
  return ['purchase_order', 'purchaseorder', 'work_order', 'workorder'].includes(kind);
}

/**
 * Round a number to specified decimal places
 */
function round(value: number, decimals = 2): number {
  return Math.round(value * 10 ** decimals) / 10 ** decimals;
}

/**
 * Get default quantity envelope based on transaction type
 */
function getDefaultQuantity(transactionType: string, quantity: number = 0): Record<string, unknown> {
  const kind = transactionType.toLowerCase().replace(/-/g, '_');
  
  if (['proposal'].includes(kind)) {
    return {
      placed: quantity,
      ordered: 0,
      remaining: quantity,
      is_fixed: false,
      precision: 2,
      is_blanket: false,
      increment: 0,
    };
  }
  
  if (['sales_order', 'salesorder', 'order'].includes(kind)) {
    return {
      placed: quantity,
      invoiced: 0,
      remaining: quantity,
      is_fixed: false,
      precision: 2,
      is_blanket: false,
      increment: 0,
    };
  }
  
  if (['invoice'].includes(kind)) {
    return {
      placed: quantity,
      packed: 0,
      remaining: quantity,
      is_fixed: false,
      precision: 2,
      is_blanket: false,
      increment: 0,
    };
  }
  
  if (['purchase_order', 'purchaseorder', 'work_order', 'workorder'].includes(kind)) {
    return {
      placed: quantity,
      received: 0,
      remaining: quantity,
      is_fixed: false,
      precision: 2,
      is_blanket: false,
      increment: 0,
    };
  }
  
  // Default
  return {
    placed: quantity,
    remaining: quantity,
    is_fixed: false,
    precision: 2,
  };
}

/**
 * Get default price envelope
 */
function getDefaultPrice(unitPrice: number = 0, quantity: number = 0): Record<string, unknown> {
  return {
    unit: unitPrice,
    unit_base: unitPrice,
    discount_percent: 0,
    discount_amount: 0,
    extended: round(unitPrice * quantity),
    is_fixed: false,
    precision: 2,
  };
}

/**
 * Get default cost envelope
 */
function getDefaultCost(unitCost: number = 0, quantity: number = 0): Record<string, unknown> {
  return {
    unit: unitCost,
    unit_base: unitCost,
    discount_percent: 0,
    discount_amount: 0,
    extended: round(unitCost * quantity),
    shipping: 0,
    handling: 0,
    freight: 0,
    commissions: 0,
    tax_rate: 0,
    tax: 0,
    is_fixed: false,
    precision: 2,
    tax_code: '',
    tax_code_id: 0,
    tax_lookup_id: 0,
  };
}

/**
 * Get default item envelope
 */
function getDefaultItem(): Record<string, unknown> {
  return {
    item_id: null,
    ida_item: '',
    uuid_item: '',
    description: '',
    description_text: '',
    time_lead: null,
    locations: [],
    unit_measure: 'EA',
    sequence: 0,
    line_number: 0,
    is_deleted: false,
    is_active: true,
    is_archived: false,
  };
}

// ============================================================================
// Line Item Service Class
// ============================================================================

export class LineItemService {
  private config: LineItemServiceConfig;

  constructor(config: Partial<LineItemServiceConfig> = {}) {
    this.config = {
      transactionType: config.transactionType ?? 'sales_order',
      useCost: config.useCost ?? !isSalesTransaction(config.transactionType ?? 'sales_order'),
      priceField: config.priceField ?? (isSalesTransaction(config.transactionType ?? 'sales_order') ? 'price' : 'cost'),
    };
  }

  /**
   * Create a new line from a catalog item search result
   */
  addItem(item: ItemSearchResult, quantity: number, options: AddItemOptions = {}): TransactionLine {
    const itemCode = resolveItemCode(item);
    const description = resolveItemDescription(item);
    const unitPrice = options.unitPrice ?? resolveUnitPrice(item);
    const unitCost = options.unitCost ?? resolveUnitCost(item);
    const itemId = item.id ?? item.item_id ?? item.itemId ?? null;
    const unitMeasure = String(item.unit_of_measure ?? item.unitOfMeasure ?? item.unit_measure ?? 'EA');

    // Build item envelope
    const itemEnvelope = {
      ...getDefaultItem(),
      item_id: itemId,
      ida_item: itemCode,
      description: description,
      description_text: description,
      unit_measure: unitMeasure,
    };

    // Build quantity envelope
    const quantityEnvelope = getDefaultQuantity(this.config.transactionType, quantity);

    // Build price envelope (for sales transactions)
    let priceEnvelope: Record<string, unknown> | undefined;
    if (isSalesTransaction(this.config.transactionType)) {
      priceEnvelope = getDefaultPrice(unitPrice, quantity);
      
      // Apply discount if provided
      if (options.discountPercent) {
        const gross = unitPrice * quantity;
        const discountAmount = gross * (options.discountPercent / 100);
        priceEnvelope.discount_percent = options.discountPercent;
        priceEnvelope.discount_amount = round(discountAmount);
        priceEnvelope.extended = round(gross - discountAmount);
      }
    }

    // Build cost envelope
    const costEnvelope = getDefaultCost(unitCost, quantity);

    // Construct the line
    const newLine: TransactionLine = {
      _dirty: true,
      item: itemEnvelope,
      quantity: quantityEnvelope,
      cost: costEnvelope,
      ...(priceEnvelope ? { price: priceEnvelope } : {}),
    } as unknown as TransactionLine;

    return newLine;
  }

  /**
   * Update quantity on a line and recalculate extensions
   */
  updateQuantity(line: TransactionLine, quantity: number): TransactionLine {
    const updatedLine = { ...line, _dirty: true };
    
    // Update quantity
    if (typeof updatedLine.quantity === 'object' && updatedLine.quantity !== null) {
      updatedLine.quantity = { ...updatedLine.quantity, placed: quantity };
    } else {
      updatedLine.quantity = getDefaultQuantity(this.config.transactionType, quantity);
    }

    // Recalculate
    return this.recalculateLine(updatedLine);
  }

  /**
   * Update unit price on a line and recalculate extensions
   */
  updatePrice(line: TransactionLine, unitPrice: number): TransactionLine {
    if (!isSalesTransaction(this.config.transactionType)) {
      console.warn('Cannot update price on execution-side transactions');
      return line;
    }

    const updatedLine = { ...line, _dirty: true };
    
    if (typeof updatedLine.price === 'object' && updatedLine.price !== null) {
      updatedLine.price = { ...updatedLine.price, unit: unitPrice };
    } else {
      const qty = this.getQuantity(updatedLine);
      updatedLine.price = getDefaultPrice(unitPrice, qty);
    }

    return this.recalculateLine(updatedLine);
  }

  /**
   * Update unit cost on a line and recalculate extensions
   */
  updateCost(line: TransactionLine, unitCost: number): TransactionLine {
    const updatedLine = { ...line, _dirty: true };
    
    if (typeof updatedLine.cost === 'object' && updatedLine.cost !== null) {
      updatedLine.cost = { ...updatedLine.cost, unit: unitCost };
    } else {
      const qty = this.getQuantity(updatedLine);
      updatedLine.cost = getDefaultCost(unitCost, qty);
    }

    return this.recalculateLine(updatedLine);
  }

  /**
   * Apply a discount to a line
   */
  applyDiscount(line: TransactionLine, discountPct: number): TransactionLine {
    if (!isSalesTransaction(this.config.transactionType)) {
      console.warn('Discounts are typically applied to sales transactions');
    }

    const updatedLine = { ...line, _dirty: true };
    
    if (typeof updatedLine.price === 'object' && updatedLine.price !== null) {
      const unitPrice = (updatedLine.price as Record<string, unknown>).unit as number ?? 0;
      const qty = this.getQuantity(updatedLine);
      const gross = unitPrice * qty;
      const discountAmount = gross * (discountPct / 100);
      
      updatedLine.price = {
        ...updatedLine.price,
        discount_percent: discountPct,
        discount_amount: round(discountAmount),
        extended: round(gross - discountAmount),
      };
    }

    return updatedLine;
  }

  /**
   * Mark a line as deleted (soft delete)
   */
  deleteLine(line: TransactionLine): TransactionLine {
    const updatedLine = { ...line, _dirty: true };
    
    if (typeof updatedLine.item === 'object' && updatedLine.item !== null) {
      updatedLine.item = { ...updatedLine.item, is_deleted: true };
    } else {
      updatedLine.item = { ...getDefaultItem(), is_deleted: true };
    }

    return updatedLine;
  }

  /**
   * Duplicate a line
   */
  duplicateLine(line: TransactionLine): TransactionLine {
    // Create a deep copy without id
    const { id, ...rest } = line as TransactionLine & { id?: number };
    
    return {
      ...JSON.parse(JSON.stringify(rest)),
      _dirty: true,
    } as TransactionLine;
  }

  /**
   * Calculate line values (price and cost extensions)
   */
  calculateLine(line: TransactionLine): LineCalculation {
    const qty = this.getQuantity(line);
    const unitPrice = this.getUnitPrice(line);
    const discountPc = this.getDiscountPercent(line);
    const unitCost = this.getUnitCost(line);
    const costDiscountPc = this.getCostDiscountPercent(line);

    // Price calculations
    const gross = qty * unitPrice;
    const discountAmount = gross * (discountPc / 100);
    const extended = gross - discountAmount;

    // Cost calculations
    const grossCost = qty * unitCost;
    const discountCost = grossCost * (costDiscountPc / 100);
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
  }

  /**
   * Recalculate extended values on a line
   */
  recalculateLine(line: TransactionLine): TransactionLine {
    const calc = this.calculateLine(line);
    const updatedLine = { ...line };

    // Update price extended
    if (typeof updatedLine.price === 'object' && updatedLine.price !== null) {
      updatedLine.price = {
        ...updatedLine.price,
        extended: calc.extended,
        discount_amount: calc.discountAmount,
      };
    }

    // Update cost extended
    if (typeof updatedLine.cost === 'object' && updatedLine.cost !== null) {
      updatedLine.cost = {
        ...updatedLine.cost,
        extended: calc.costExtended,
      };
    }

    return updatedLine;
  }

  // ---------------------------------------------------------------------------
  // Helper getters
  // ---------------------------------------------------------------------------

  private getQuantity(line: TransactionLine): number {
    if (typeof line.quantity === 'object' && line.quantity !== null) {
      const q = line.quantity as Record<string, unknown>;
      return Number(q.placed ?? q.ordered ?? 0) || 0;
    }
    return 0;
  }

  private getUnitPrice(line: TransactionLine): number {
    if (typeof line.price === 'object' && line.price !== null) {
      const p = line.price as Record<string, unknown>;
      return Number(p.unit ?? 0) || 0;
    }
    return 0;
  }

  private getDiscountPercent(line: TransactionLine): number {
    if (typeof line.price === 'object' && line.price !== null) {
      const p = line.price as Record<string, unknown>;
      return Number(p.discount_percent ?? 0) || 0;
    }
    return 0;
  }

  private getUnitCost(line: TransactionLine): number {
    if (typeof line.cost === 'object' && line.cost !== null) {
      const c = line.cost as Record<string, unknown>;
      return Number(c.unit ?? 0) || 0;
    }
    return 0;
  }

  private getCostDiscountPercent(line: TransactionLine): number {
    if (typeof line.cost === 'object' && line.cost !== null) {
      const c = line.cost as Record<string, unknown>;
      return Number(c.discount_percent ?? 0) || 0;
    }
    return 0;
  }
}

// ============================================================================
// Factory Functions
// ============================================================================

/**
 * Create a LineItemService configured for sales transactions
 */
export function createSalesLineItemService(transactionType: 'sales_order' | 'proposal' | 'invoice' = 'sales_order'): LineItemService {
  return new LineItemService({
    transactionType,
    useCost: false,
    priceField: 'price',
  });
}

/**
 * Create a LineItemService configured for purchase transactions
 */
export function createPurchaseLineItemService(transactionType: 'purchase_order' | 'work_order' = 'purchase_order'): LineItemService {
  return new LineItemService({
    transactionType,
    useCost: true,
    priceField: 'cost',
  });
}

// ============================================================================
// Convenience Functions
// ============================================================================

/**
 * Add an item to a transaction's lines array (pure function)
 */
export function addItemToLines(
  lines: TransactionLine[],
  item: ItemSearchResult,
  quantity: number,
  transactionType: TransactionType,
  options: AddItemOptions = {}
): TransactionLine[] {
  const service = new LineItemService({ transactionType });
  const newLine = service.addItem(item, quantity, options);
  return [...lines, newLine];
}

/**
 * Update a line in an array by index
 */
export function updateLineInArray(
  lines: TransactionLine[],
  index: number,
  updater: (line: TransactionLine) => TransactionLine
): TransactionLine[] {
  return lines.map((line, i) => (i === index ? updater(line) : line));
}

/**
 * Remove a line from an array (soft delete)
 */
export function removeLineFromArray(
  lines: TransactionLine[],
  index: number
): TransactionLine[] {
  const service = new LineItemService();
  return lines.map((line, i) => (i === index ? service.deleteLine(line) : line));
}

/**
 * Filter out deleted lines
 */
export function getActiveLines(lines: TransactionLine[]): TransactionLine[] {
  return lines.filter(line => {
    if (typeof line.item === 'object' && line.item !== null) {
      const item = line.item as Record<string, unknown>;
      return !item.is_deleted;
    }
    return true;
  });
}

// Default export
export default LineItemService;
