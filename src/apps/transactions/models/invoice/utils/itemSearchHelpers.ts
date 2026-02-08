import type { ItemSearchResult } from "../types/itemSearchType";

export function resolveItemCode(item: ItemSearchResult): string {
  return (
    item.ida_item ||
    item.item_num ||
    item.itemNum ||
    item.item_id?.toString() ||
    item.id?.toString() ||
    ""
  );
}

export function resolveItemDescription(item: ItemSearchResult): string {
  return (
    item.description ||
    item.description_text ||
    item.name ||
    resolveItemCode(item) ||
    "Item"
  );
}

export function resolveItemKey(item: ItemSearchResult): string {
  const code = resolveItemCode(item);
  if (code) {
    return code;
  }
  const id = item.id || item.item_id || item.itemId;
  return id ? `item-${id}` : "";
}

/**
 * Resolve unit price based on price level
 * If item.price is an object with price levels (base, wholesale, distributor, sample),
 * looks up item.price[priceLevel], falling back to item.price.base if level not found.
 * priceLevel defaults to "base" if null/undefined.
 */
export function resolveUnitPrice(
  item: ItemSearchResult,
  priceLevel?: string | null,
): number {
  // Default price level to "base" if not provided
  const level = priceLevel || "base";

  // Check if item.price is an object with price levels
  if (item.price && typeof item.price === "object") {
    const priceObj = item.price as Record<string, unknown>;
    // Try the requested price level first, fall back to base
    const levelValue = priceObj[level] ?? priceObj.base;
    if (typeof levelValue === "number" && levelValue >= 0) return levelValue;
    if (typeof levelValue === "string") {
      const parsed = Number.parseFloat(levelValue);
      if (!Number.isNaN(parsed) && parsed >= 0) return parsed;
    }
  }

  // Legacy fallback for non-object price fields
  const candidates = [item.unit_price, item.price, item.priceA, item.price_a];

  for (const candidate of candidates) {
    if (typeof candidate === "number" && candidate >= 0) {
      return candidate;
    }
    if (typeof candidate === "string") {
      const parsed = Number.parseFloat(candidate);
      if (!Number.isNaN(parsed) && parsed >= 0) {
        return parsed;
      }
    }
  }

  return 0;
}

export function resolveUnitCost(item: ItemSearchResult): number {
  const candidates = [item.unit_cost, item.cost, item.costA];

  for (const candidate of candidates) {
    if (typeof candidate === "number" && candidate >= 0) {
      return candidate;
    }
    if (typeof candidate === "string") {
      const parsed = Number.parseFloat(candidate);
      if (!Number.isNaN(parsed) && parsed >= 0) {
        return parsed;
      }
    }
  }

  return 0;
}

export function resolveQtyOnHand(item: ItemSearchResult): number {
  const candidates = [item.qty_on_hand, item.qtyOnHand];

  for (const candidate of candidates) {
    if (typeof candidate === "number" && candidate >= 0) {
      return candidate;
    }
    if (typeof candidate === "string") {
      const parsed = Number.parseFloat(candidate);
      if (!Number.isNaN(parsed) && parsed >= 0) {
        return parsed;
      }
    }
  }

  return 0;
}
