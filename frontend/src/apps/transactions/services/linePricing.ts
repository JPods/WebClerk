/**
 * Line pricing — the browser asks, the server decides (Bill, 2026-10-22).
 *
 * One call returns both figures for each item: the sell price (resolve_price — catalog,
 * price level, quantity break, margin floor) with the cost it is measured against,
 * and the buy-side cost (resolve_cost — the company cost basis) with the list price it
 * feeds. Nothing in the browser chooses a price level or a cost basis.
 *
 * Server: backend/apps/products/services/price_resolver.py → price_lines
 */
import { manageAction } from '@/api/wcapi';

export interface PriceFigure {
  price: number;
  list_price: number;
  resolved_by: 'price_locked' | 'catalog_line' | 'price_level' | 'list_price';
  price_level: string;
  qty_break: Record<string, unknown> | null;
  catalog_id: number | null;
  catalog_name: string;
  catalog_line_id: number | null;
  discount_pct: number;
  discount_amount: number;
  unit_cost: number;
  cost_basis: string;
  margin_pct: number | null;
  margin_floor: number;
  below_margin_floor: boolean;
  price_locked: boolean;
}

export interface CostFigure {
  unit: number;
  basis: string;
  list_price: number;
  margin_pct: number | null;
}

export interface LineFigures {
  item_id: number;
  qty: number;
  price: PriceFigure;
  cost: CostFigure;
}

export interface LinePricingContext {
  /** The document's customer — its catalogs and price level apply. */
  customerId?: number | null;
  /** The document's (or line's) price level; blank = the customer's. */
  priceLevel?: string | null;
}

export async function priceLines(
  items: { item_id: number; qty: number }[],
  ctx: LinePricingContext = {},
): Promise<{ level: string; lines: LineFigures[] }> {
  return manageAction('price_lines', {
    items,
    customer_id: ctx.customerId || null,
    price_level: ctx.priceLevel || null,
  });
}
