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

export function resolveUnitPrice(item: ItemSearchResult): number {
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
