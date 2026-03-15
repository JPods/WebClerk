/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Line Item Service - Single Point of Authority for transaction line management
 * 
 * Handles adding, updating, and managing transaction line items across all
 * transaction types (order, proposal, invoice, purchase, workorder).
 * 
 * Key behaviors:
 * - Sales transactions: price.unit is the primary value
 * - Purchase transactions: cost.unit is the primary value
 */

import { wcapi } from '../../../api/wcapi';
import type { TransactionLine } from '../types/transactionTypes';
import {
  ItemSearchResult,
  resolveItemCode,
  resolveItemDescription,
  resolveUnitPrice,
  resolveUnitCost,
} from '../components/TransactionItemSearch';
import { round, toNumber } from './calculationUtils';

// ============================================================================
// Types
// ============================================================================

/**
 * The 5 transaction types that go through `saveTransactionWithLines()`
 * and `LineItemService`. Receipt is excluded because it uses a separate
 * backend save path (flow.py: receive_purchase / complete_workorder /
 * adjust_inventory) and doesn't participate in line-level pending or
 * dirty-tracking via this service.
 */
export type TransactionType = 'order' | 'proposal' | 'invoice' | 'purchase' | 'workorder';

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
  return ['order', 'proposal', 'invoice'].includes(kind);
}

/**
 * Determine if a transaction type is exec-side (uses cost as primary)
 */
export function isExecTransaction(transactionType: string): boolean {
  const kind = transactionType.toLowerCase().replace(/-/g, '_');
  return ['purchase', 'workorder'].includes(kind);
}

// round() and toNumber() are imported from calculationUtils.ts

/**
 * Get default quantity envelope based on transaction type.
 *
 * Canonical keys (matches wc3 base_line_model.default_quantity):
 *   staged     — quantity committed on this line (= active for standalone)
 *   active     — user-entered quantity (always the primary input)
 *   remaining  — uncommitted qty available for downstream transfer
 *   is_fixed, precision, is_blanket, increment — control/metadata
 *
 * All types: remaining = active (or active − children_active.sum if has children)
 */
function getDefaultQuantity(_transactionType: string, quantity: number = 0): Record<string, unknown> {
  return {
    staged: quantity,
    active: quantity,
    remaining: quantity,
    is_fixed: false,
    precision: 2,
    is_blanket: false,
    increment: 0,
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
      transactionType: config.transactionType ?? 'order',
      useCost: config.useCost ?? !isSalesTransaction(config.transactionType ?? 'order'),
      priceField: config.priceField ?? (isSalesTransaction(config.transactionType ?? 'order') ? 'price' : 'cost'),
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
   * Update quantity on a line and recalculate extensions.
   *
   * User always edits 'active'. For standalone (no parent), staged mirrors active.
   * All lines: remaining = active (or active − children_active.sum).
   * Parent's children_active tracker is updated separately at save time.
   *
   * Matches wc3 normalize_quantity_map() semantics.
   */
  updateQuantity(line: TransactionLine, quantity: number, hasParent = false): TransactionLine {
    const updatedLine = { ...line, _dirty: true };

    if (typeof updatedLine.quantity === 'object' && updatedLine.quantity !== null) {
      const staged = hasParent
        ? ((updatedLine.quantity as Record<string, unknown>).staged as number ?? quantity)
        : quantity;
      // Remaining = active (universal formula; children_active tracked server-side)
      const remaining = quantity;
      updatedLine.quantity = {
        ...updatedLine.quantity,
        active: quantity,
        staged,
        remaining,
      };
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
   *
   * Mirrors WC3 `_calculate_extended_price()` at base_line_model.py:388.
   * Uses per-line precision from price.precision / cost.precision.
   */
  calculateLine(line: TransactionLine): LineCalculation {
    const qty = this.getQuantity(line);
    const unitPrice = this.getUnitPrice(line);
    const discountPc = this.getDiscountPercent(line);
    const unitCost = this.getUnitCost(line);
    const costDiscountPc = this.getCostDiscountPercent(line);

    // Read precision from line envelopes (WC3 default: 2)
    const pricePrecision = this.getPrecision(line, 'price');
    const costPrecision = this.getPrecision(line, 'cost');

    // Price calculations  (sell-side)
    const gross = round(qty * unitPrice, pricePrecision);
    const discountAmount = this.getDiscountAmount(line, gross, discountPc, pricePrecision);
    const extended = round(gross - discountAmount, pricePrecision);

    // Cost calculations
    const grossCost = round(qty * unitCost, costPrecision);
    const discountCost = this.getCostDiscountAmount(line, grossCost, costDiscountPc, costPrecision);
    const costExtended = round(grossCost - discountCost, costPrecision);

    // Margin (internal use only)
    const margin = round(extended - costExtended);
    const marginPc = extended > 0 ? round((margin / extended) * 100, 2) : 0;

    return {
      gross,
      discountAmount,
      extended,
      grossCost,
      discountCost,
      costExtended,
      margin,
      marginPc,
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
      return Number(q.staged ?? 0) || 0;
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

  /**
   * Read precision from a line's price or cost envelope.
   * Falls back to 2 (WC3 default).
   */
  private getPrecision(line: TransactionLine, envelope: 'price' | 'cost'): number {
    const env = line[envelope];
    if (typeof env === 'object' && env !== null) {
      const p = Number((env as Record<string, unknown>).precision);
      return Number.isFinite(p) && p >= 0 ? p : 2;
    }
    return 2;
  }

  /**
   * Resolve discount amount — mirrors WC3 logic:
   *   if discount_amount is explicitly set (non-zero) → use it
   *   else → compute from gross × (discount_percent / 100)
   */
  private getDiscountAmount(
    line: TransactionLine,
    gross: number,
    discountPc: number,
    precision = 2,
  ): number {
    if (typeof line.price === 'object' && line.price !== null) {
      const p = line.price as Record<string, unknown>;
      const explicit = Number(p.discount_amount ?? 0);
      // WC3: use explicit if set AND (non-zero OR percent is zero)
      if (explicit !== 0) {
        return round(explicit, precision);
      }
    }
    return round(gross * (discountPc / 100), precision);
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

  private getCostDiscountAmount(
    line: TransactionLine,
    grossCost: number,
    discountPc: number,
    precision = 2,
  ): number {
    if (typeof line.cost === 'object' && line.cost !== null) {
      const c = line.cost as Record<string, unknown>;
      const explicit = Number(c.discount_amount ?? 0);
      if (explicit !== 0) {
        return round(explicit, precision);
      }
    }
    return round(grossCost * (discountPc / 100), precision);
  }
}

// ============================================================================
// Factory Functions
// ============================================================================

/**
 * Create a LineItemService configured for sales transactions
 */
export function createSalesLineItemService(transactionType: 'order' | 'proposal' | 'invoice' = 'order'): LineItemService {
  return new LineItemService({
    transactionType,
    useCost: false,
    priceField: 'price',
  });
}

/**
 * Create a LineItemService configured for purchase transactions
 */
export function createPurchaseLineItemService(transactionType: 'purchase' | 'workorder' = 'purchase'): LineItemService {
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
